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




from asyncio import gather, Semaphore

from asyncio import as_completed, Lock

@router.post("/start_task", summary="启动审阅任务")
async def start_task(
    request: ReviewTaskCreateRequest,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    if not request.session_id:
        raise HTTPException(status_code=400, detail="会话ID不能为空")
    MAX_CONCURRENT = request.max_concurrent
    semaphore = Semaphore(MAX_CONCURRENT)
    async def event_generator():
        #  检查任务是否已经存在 存在进行删除覆盖
        existing_task = await CRUDReviewTask.get_review_task(db, request.session_id)
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
        contract_content_path = contract.contract_content_path
        with open(contract_content_path, "r", encoding="utf-8") as f:
            contract_content = f.read()

        # 执行审阅
        model_config = await get_default_model_by_type(db, model_type="chat")

        async_client = AsyncClient(
            api_key=model_config.api_key,
            base_url=model_config.api_endpoint
        )
        # 分割合同内容
        chunks = split_text_by_length(contract_content, max_length=4000)
        global_index = 1
        index_lock = Lock()  # 保护 global_index 自增

        async def process_chunk(idx: int, chunk_content: str):
            try:
                async with semaphore:
                    context = f"这是第 {idx + 1} 个分块，共 {len(chunks)} 个。"
                    modifications = await contract_review_service.review_contract(
                        async_client, model_config, chunk_content, review_task.stance, "", context
                    )
                return idx, modifications
            except Exception as e:
                logger.error(f"Chunk {idx} 审阅失败: {e}")
                return idx, []

        tasks = [process_chunk(idx, chunk) for idx, chunk in enumerate(chunks)]

        # 使用 as_completed 实现“谁先完成谁先处理”
        for coro in as_completed(tasks):
            idx, modifications = await coro

            # 为每个 modification 分配全局 index（线程安全）
            local_indices = []
            async with index_lock:
                for _ in modifications:
                    local_indices.append(global_index)
                    global_index += 1

            # 写入 DB 并立即 yield
            for mod, idx_val in zip(modifications, local_indices):
                review_result = await CRUDReviewResult.create_review_result(
                    db=db,
                    session_id=review_task.session_id,
                    task_id=review_task.id,
                    index=idx_val,
                    original_content=mod["original_content"],
                    risk_analysis=mod["risk_analysis"],
                    risk_level=mod["risk_level"],
                    suggested_content=mod["suggested_content"]
                )
                yield json.dumps(
                    ReviewTaskSSEResponse(event="message", data=review_result.dict()).model_dump(),
                    ensure_ascii=False
                )

            logger.info(f"任务 {review_task.id} 第 {idx + 1} 个分块审阅完成，发现 {len(modifications)} 个修改点")

        # 发送总结
        total_issues = global_index - 1
        overall_risk = "低"
        if total_issues > 10:
            overall_risk = "高"
        elif total_issues > 5:
            overall_risk = "中"
        summary = f"共发现 {total_issues} 个潜在风险点，整体风险等级为 {overall_risk}。"
        suggestion = f"建议重点关注风险等级较高的条款，并根据 {review_task.stance} 立场进行相应调整。"
        yield json.dumps(
            ReviewTaskSSEResponse(
                event="end",
                data={"type": "summary", "summary": summary, "suggestion": suggestion}
            ).model_dump(),
            ensure_ascii=False
        )

    return EventSourceResponse(event_generator())
