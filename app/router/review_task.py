"""
@Project ：Contract_Review_backend-Py 
@File    ：review_task.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/22 14:13 
"""
import logging
import asyncio
import json
from re import A

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from openai import BaseModel
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.orm import Session as DBSession

from app.middlewares.auth import get_current_user
from app.schemas.review_task import (
    ReviewTaskCreateRequest,ReviewTaskSSEResponse
)
from app.curd.review_task import CRUDReviewTask, CRUDReviewResult
from app.curd.contract_file import CRUDContract
from app.core.dependencies import get_db
from app.models.user import User
from app.services.contract_review import ContractReviewService
from app.utils.mcp_client import MCPClient
from app.utils.content_slicer import split_text_by_length
from openai import AsyncClient
from app.curd.model_configs import get_default_model_by_type

logger = logging.getLogger(__name__)

router = APIRouter(tags=["合同审阅"])
"""
合同审阅相关接口
"""


# @router.post(
#         "/create",
#         summary="创建审阅任务",
#         response_model=GenericResponse[ReviewTaskResponse]
# )
# async def create_review(
#         request: ReviewTaskCreateRequest,
#         current_user: User = Depends(get_current_user),
#         db: DBSession = Depends(get_db)
# ) -> GenericResponse[ReviewTaskResponse]:
#     """创建审阅任务"""
#     try:
#         # 创建会话
#
#         review_task = CRUDReviewTask.create_review_task(db, current_user.id, request)
#         return GenericResponse(
#             code=200,
#             msg="审阅任务创建成功",
#             data=ReviewTaskResponse(
#                 id=review_task.id,
#                 file_id=review_task.file_id,
#                 session_id=review_task.session_id,
#                 user_id=review_task.user_id,
#                 stance=review_task.stance,
#                 intensity=review_task.intensity,
#                 description=review_task.description,
#                 status=review_task.status,
#                 created_at=review_task.created_at,
#                 completed_at=review_task.completed_at
#             )
#         )
#     except Exception as e:
#         logger.error(f"创建审阅任务失败: {e}")
#         raise HTTPException(status_code=500, detail=f"创建审阅任务失败: {str(e)}")



@router.post("/start_task",summary="启动审阅任务")
async def start_task(
        request: ReviewTaskCreateRequest,
        current_user: User = Depends(get_current_user),
        db: DBSession = Depends(get_db)
):
    """启动审阅任务"""
    if not request.session_id:
        raise HTTPException(status_code=400, detail="会话ID不能为空")

    async def event_generator():
            #  检查任务是否已经存在 存在进行删除覆盖
            existing_task =await CRUDReviewTask.get_review_task(db, request.session_id)
            if existing_task:
                await CRUDReviewTask.delete_review_task(db, existing_task.id)
                await CRUDReviewResult.delete_review_result(db, existing_task.id)
            # 创建任务

            review_task = await CRUDReviewTask.create_review_task(db, current_user.id, request)

            if not review_task:
                yield json.dumps(
                        ReviewTaskSSEResponse(
                        event="error",
                        data={"message": "任务不存在"}).model_dump(), ensure_ascii=False)
            await CRUDReviewTask.update_task_status(db, review_task.id, "processing")
            contract = await CRUDContract.get_contract_file(db, review_task.file_id)
            mcp_client = MCPClient()
            await mcp_client.initialize()
            contract_review_service = ContractReviewService(mcp_client)
            """
            原始文本提取（有问题需更改）
                file_ext = contract.file_path.split('.')[-1].lower()
                if file_ext == 'pdf':
                    contract_content = await mcp_client.extract_pdf_document_content(contract.file_path)
                else:
                    contract_content = await mcp_client.extract_document_content(contract.file_path)
            """
            # 文件内容提取在上传接口，这里直接从数据库获取
            contract_content=contract.contract_content
            # 执行审阅
            model_config = await get_default_model_by_type(db, model_type="chat") 

            async_client = AsyncClient(
                api_key=model_config.api_key,
                base_url=model_config.api_endpoint
            )
            # 分割合同内容
            chunks = split_text_by_length(contract_content, max_length=4000)
            global_index = 1
            for idx, chunk_content in enumerate(chunks):
                try:
                    # 构建审阅上下文
                    context = ""
                    if idx > 0:
                        context = f"这是第 {idx + 1} 个分块，前面已审阅 {idx} 个分块。"
                    modifications = await contract_review_service.review_contract(
                        async_client,model_config, chunk_content, review_task.stance, "", context
                    )
                    for j, modification in enumerate(modifications):
                        review_result=await CRUDReviewResult.create_review_result(
                            db=db,
                            session_id=review_task.session_id,
                            task_id=review_task.id,
                            index=global_index,
                            original_content=modifications[j]["original_content"],
                            risk_analysis=modification["risk_analysis"],
                            risk_level=modification["risk_level"],
                            suggested_content=modification["suggested_content"]
                        )
                        global_index += 1
                        yield json.dumps(
                            ReviewTaskSSEResponse(
                                event="message",
                                data=review_result.dict()
                            ).model_dump(), ensure_ascii=False)
                    logger.info(f"任务 {review_task.id} 第 {idx + 1} 个分块审阅完成，发现 {len(modifications)} 个修改点")
                except Exception as e:
                    logger.error(f"任务 {review_task.id} 第 {idx + 1} 个分块审阅失败: {e}")
                    continue

            # 分析整体风险等级
            overall_risk = "低"
            if global_index > 10:
                overall_risk = "高"
            elif global_index > 5:
                overall_risk = "中"
            summary = f"共发现 {global_index} 个潜在风险点，整体风险等级为 {overall_risk}。"
            suggestion = f"建议重点关注风险等级较高的条款，并根据 {review_task.stance} 立场进行相应调整。"
            yield json.dumps(
                    ReviewTaskSSEResponse(
                        event="end",
                        data={
                            "type": "summary",
                            "summary": summary,
                            "suggestion": suggestion
                        }
                    ).model_dump(), ensure_ascii=False)
    return  EventSourceResponse(
        event_generator()
    )


