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
from app.schemas.base import GenericResponse
from app.schemas.review_task import (
    ReviewTaskCreateRequest, ReviewTaskSSEResponse, AcceptRiskPointRequest
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
from asyncio import  Semaphore
logger = logging.getLogger(__name__)

router = APIRouter(tags=["合同审阅"])
"""
合同审阅相关接口
"""


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
        review_task = await CRUDReviewTask.create_review_task(db, current_user.id, request)

        if not review_task:
            yield json.dumps(
                ReviewTaskSSEResponse(
                    event="error",
                    data={"message": "任务不存在"}).model_dump(), ensure_ascii=False)
        await CRUDReviewTask.update_task_status(db, review_task.id, "processing")
        contract = await CRUDContract.get_contract_file(db, review_task.file_id)
        if contract.type == "uploaded":
            yield json.dumps(
                ReviewTaskSSEResponse(event="error", data={"message": "当前文件为上传文件，不支持审阅"}).model_dump(),
                ensure_ascii=False
            )

        mcp_client = MCPClient()
        await mcp_client.initialize()
        contract_review_service = ContractReviewService(mcp_client)
        contract_content_path = contract.contract_content_path
        with open(contract_content_path, "r", encoding="utf-8") as f:
            contract_content = f.read()

        model_config = await get_default_model_by_type(db, model_type="chat")

        async_client = AsyncClient(
            api_key=model_config.api_key,
            base_url=model_config.api_endpoint
        )
        chunks = split_text_by_length(contract_content, max_length=4000)
        n = len(chunks)

        result_queue = asyncio.Queue()
        received_results = {}
        next_to_emit = 0
        global_index = 1
        tasks = []

        async def process_chunk(idx: int, content: str):
            try:
                async with semaphore:
                    context = f"这是第 {idx + 1} 个分块，共 {n} 个。"
                    mods = await contract_review_service.review_contract(
                        async_client, model_config, content, review_task.stance, "",
                        context, contract_type=review_task.contract_type
                    )
            except Exception as e:
                logger.error(f"Chunk {idx} 审阅失败: {e}")
                mods = []
            await result_queue.put((idx, mods))

        try:
            for idx, chunk in enumerate(chunks):
                task = asyncio.create_task(process_chunk(idx, chunk))
                tasks.append(task)

            while next_to_emit < n:
                idx, mods = await result_queue.get()
                received_results[idx] = mods
                while next_to_emit in received_results:
                    current_mods = received_results.pop(next_to_emit)
                    for mod in current_mods:
                        review_result = await CRUDReviewResult.create_review_result(
                            db=db,
                            session_id=review_task.session_id,
                            task_id=review_task.id,
                            index=global_index,
                            original_content=mod["original_content"],
                            risk_analysis=mod["risk_analysis"],
                            risk_level=mod["risk_level"],
                            suggested_content=mod["suggested_content"]
                        )
                        yield json.dumps(
                            ReviewTaskSSEResponse(event="message", data=review_result.dict()).model_dump(),
                            ensure_ascii=False
                        )
                        global_index += 1
                    logger.info(f"Chunk {next_to_emit} 完成，产出 {len(current_mods)} 条")
                    next_to_emit += 1

            total_issues = global_index - 1
            overall_risk = "高" if total_issues > 10 else "中" if total_issues > 5 else "低"
            yield json.dumps(
                ReviewTaskSSEResponse(
                    event="end",
                    data={
                        "type": "summary",
                        "summary": f"共发现 {total_issues} 个潜在风险点，整体风险等级为 {overall_risk}。",
                        "suggestion": f"建议重点关注高风险条款，并根据 {review_task.stance} 立场调整。"
                    }
                ).model_dump(),
                ensure_ascii=False
            )

        finally:
            pending_tasks = [t for t in tasks if not t.done()]
            if pending_tasks:
                logger.info(f"检测到客户端断开或异常，正在取消 {len(pending_tasks)} 个未完成审阅任务...")
                for task in pending_tasks:
                    task.cancel()

                await asyncio.gather(*pending_tasks, return_exceptions=True)

    return EventSourceResponse(event_generator())

@router.post("/accept_risk_point", summary="接受风险点修订",dependencies=[])
async def accept_risk_point(
        request: AcceptRiskPointRequest,
        current_user: User = Depends(get_current_user),
        db: DBSession = Depends(get_db)
):
    print("="*50)
    if not current_user:
        return GenericResponse(code=401, msg="用户未登录")
    success = await CRUDReviewResult.accept_risk_point(
        db=db,
        session_id=request.session_id,
        task_id=request.task_id,
        index=request.index,
        is_accepted=request.is_accepted,
        user_id=current_user.id,
    )

    if not success:
        return GenericResponse(code=400, msg="风险点不存在或未发生变更")

    return GenericResponse(code=200, msg="操作成功", data=True)
