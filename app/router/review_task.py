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

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from openai import BaseModel
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.orm import Session as DBSession

from app.middlewares.auth import get_current_user
from app.schemas.base import GenericResponse
from app.schemas.review_task import (
    ReviewTaskCreateRequest,
    ReviewTaskResponse,
    # ReviewResultResponse,
    # RiskItemResponse,
    ReviewTaskListResponse, ReviewTaskDetailResponse, ReviewTaskSSEResponse,
    # ReviewProgressResponse
)
from app.curd.review_task import CRUDReviewTask, CRUDReviewResult
from app.curd.contract_file import CRUDContract
from app.core.dependencies import get_db
from app.models.user import User
from app.services.contract_review import ContractReviewService
from app.utils.document_parsing import docx2md, mk_pdf2docx
from app.utils.mcp_client import MCPClient
from app.utils.content_slicer import split_text_by_length

logger = logging.getLogger(__name__)

router = APIRouter(tags=["合同审阅"])
"""
合同审阅相关接口
"""

# 全局变量存储审阅进度
review_progress = {}

# 全局队列：按任务ID存储审阅流结果（每个chunk完成即推送）
stream_queues: dict[int, asyncio.Queue] = {}



# @router.post("/start/{task_id}", response_model=GenericResponse[dict])
# async def start_review_task(
#     task_id: int,
#     background_tasks: BackgroundTasks,
#     current_user: User = Depends(get_current_user),
#     db: DBSession = Depends(get_db)
# ):
#     """开始执行审阅任务"""
#     try:
#         # 获取审阅任务
#         review_task = CRUDReviewTask.get_review_task(db, task_id)
#         if not review_task:
#             raise HTTPException(status_code=404, detail="审阅任务不存在")
#
#         if review_task.user_id != current_user.id:
#             raise HTTPException(status_code=403, detail="无权限访问此任务")
#
#         if review_task.status != "pending":
#             raise HTTPException(status_code=400, detail="任务状态不允许开始审阅")
#
#         # 更新任务状态为进行中
#         CRUDReviewTask.update_task_status(db, task_id, "processing")
#
#         # 初始化审阅进度
#         review_progress[task_id] = {
#             "current_chunk": 0,
#             "total_chunks": 0,
#             "status": "processing",
#             "message": "正在准备审阅..."
#         }
#         # 初始化结果流队列（若已存在则重置）
#         stream_queues[task_id] = asyncio.Queue()
#
#         # 在后台执行审阅任务
#         background_tasks.add_task(
#             execute_review_task,
#             task_id,
#             review_task.contract_id,
#             review_task.stance,
#             review_task.intensity,
#             review_task.description,
#             current_user.id
#         )
#
#         logger.info(f"开始执行审阅任务 {task_id}")
#
#         return GenericResponse(
#             code=200,
#             msg="审阅任务已开始执行",
#             data={"task_id": task_id, "status": "processing"}
#         )
#
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"开始审阅任务失败: {e}")
#         raise HTTPException(status_code=500, detail=f"开始审阅任务失败: {str(e)}")
#
#
# @router.get("/result/{task_id}")
# async def get_review_result(
#     task_id: int,
#     current_user: User = Depends(get_current_user),
#     db: DBSession = Depends(get_db)
# ):
#     """流式返回审阅结果（按chunk）"""
#     # 权限校验
#     review_task = CRUDReviewTask.get_review_task(db, task_id)
#     if not review_task:
#         raise HTTPException(status_code=404, detail="审阅任务不存在")
#     if review_task.user_id != current_user.id:
#         raise HTTPException(status_code=403, detail="无权限访问此任务")
#
#     async def event_generator():
#         # 若没有队列，尝试创建空队列防止404，但提示状态
#         q = stream_queues.get(task_id)
#         last_progress = {"current": 0, "total": 0}
#
#         while True:
#             try:
#                 if q is None:
#                     # 任务可能已完成，返回最终快照并结束
#                     review_result = CRUDReviewTask.get_review_result(db, task_id)
#                     if review_result:
#                         risk_items = CRUDReviewTask.get_risk_items(db, review_result.id)
#                         payload = {
#                             "type": "final_snapshot",
#                             "task": {
#                                 "id": review_task.id,
#                                 "status": review_task.status,
#                             },
#                             "result": {
#                                 "overall_risk": review_result.overall_risk,
#                                 "summary": review_result.summary,
#                                 "suggestion": review_result.suggestion,
#                             },
#                             "risk_items": [
#                                 {
#                                     "id": item.id,
#                                     "clause_text": item.clause_text,
#                                     "risk_type": item.risk_type,
#                                     "risk_level": item.risk_level,
#                                     "suggestion": item.suggestion,
#                                 } for item in risk_items
#                             ]
#                         }
#                         yield {
#                             "event": "message",
#                             "data": json.dumps(payload, ensure_ascii=False)
#                         }
#                     break
#
#                 # 等待队列事件
#                 item = await asyncio.wait_for(q.get(), timeout=1.0)
#                 if item.get("type") == "chunk_result":
#                     yield {
#                         "event": "message",
#                         "data": json.dumps(item, ensure_ascii=False)
#                     }
#                 elif item.get("type") == "completed":
#                     yield {
#                         "event": "message",
#                         "data": json.dumps({"type": "completed"}, ensure_ascii=False)
#                     }
#                     break
#                 elif item.get("type") == "failed":
#                     yield {
#                         "event": "message",
#                         "data": json.dumps({"type": "failed", "error": item.get("error")}, ensure_ascii=False)
#                     }
#                     break
#             except asyncio.TimeoutError:
#                 # 可选：同步一次进度作为心跳
#                 prog = review_progress.get(task_id)
#                 if prog and (prog["current_chunk"] != last_progress["current"] or prog["total_chunks"] != last_progress["total"]):
#                     last_progress = {"current": prog["current_chunk"], "total": prog["total_chunks"]}
#                     pct = 0
#                     if prog["total_chunks"]:
#                         pct = round(prog["current_chunk"] / prog["total_chunks"] * 100, 1)
#                     yield {
#                         "event": "message",
#                         "data": json.dumps({
#                             "type": "progress",
#                             "current_chunk": prog["current_chunk"],
#                             "total_chunks": prog["total_chunks"],
#                             "percentage": pct,
#                             "status": prog.get("status")
#                         }, ensure_ascii=False)
#                     }
#                 await asyncio.sleep(0.1)
#
#     return EventSourceResponse(event_generator())
#
#
# @router.get("/progress/{task_id}")
# async def stream_review_progress(
#     task_id: int,
#     current_user: User = Depends(get_current_user),
#     db: DBSession = Depends(get_db)
# ):
#     """SSE流：每个chunk完成时推送最新进度"""
#     review_task = CRUDReviewTask.get_review_task(db, task_id)
#     if not review_task:
#         raise HTTPException(status_code=404, detail="审阅任务不存在")
#     if review_task.user_id != current_user.id:
#         raise HTTPException(status_code=403, detail="无权限访问此任务")
#
#     async def progress_events():
#         last = {"c": -1, "t": -1}
#         while True:
#             prog = review_progress.get(task_id)
#             if not prog:
#                 await asyncio.sleep(0.2)
#                 continue
#             if prog["current_chunk"] != last["c"] or prog["total_chunks"] != last["t"]:
#                 last = {"c": prog["current_chunk"], "t": prog["total_chunks"]}
#                 pct = 0
#                 if prog["total_chunks"]:
#                     pct = round(prog["current_chunk"] / prog["total_chunks"] * 100, 1)
#                 yield {
#                     "event": "message",
#                     "data": json.dumps({
#                         "type": "progress",
#                         "current_chunk": prog["current_chunk"],
#                         "total_chunks": prog["total_chunks"],
#                         "percentage": pct,
#                         "status": prog.get("status"),
#                         "message": prog.get("message")
#                     }, ensure_ascii=False)
#                 }
#             if prog.get("status") in ("completed", "failed"):
#                 break
#             await asyncio.sleep(0.3)
#
#     return EventSourceResponse(progress_events())
#

# --------------------


@router.post(
        "/create",
        summary="创建审阅任务",
        response_model=GenericResponse[ReviewTaskResponse]
)
async def create_review(
        request: ReviewTaskCreateRequest,
        current_user: User = Depends(get_current_user),
        db: DBSession = Depends(get_db)
) -> GenericResponse[ReviewTaskResponse]:
    """创建审阅任务"""
    try:
        # 创建会话

        review_task = CRUDReviewTask.create_review_task(db, current_user.id, request)
        return GenericResponse(
            code=200,
            msg="审阅任务创建成功",
            data=ReviewTaskResponse(
                id=review_task.id,
                contract_id=review_task.contract_id,
                session_id=review_task.session_id,
                user_id=review_task.user_id,
                stance=review_task.stance,
                intensity=review_task.intensity,
                description=review_task.description,
                status=review_task.status,
                created_at=review_task.created_at,
                completed_at=review_task.completed_at
            )
        )
    except Exception as e:
        logger.error(f"创建审阅任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建审阅任务失败: {str(e)}")

class StartReviewTaskRequest(BaseModel):
    task_id: str

@router.post("/start_task",summary="启动审阅任务")
async def start_task(
        request: StartReviewTaskRequest,
        current_user: User = Depends(get_current_user),
        db: DBSession = Depends(get_db)
):
    """启动审阅任务"""
    async def event_generator():
            review_task = CRUDReviewTask.get_review_user_task(
                db,
                current_user.id,
                request.task_id)
            if not review_task:

                yield json.dumps(
                        ReviewTaskSSEResponse(
                        event="error",
                        data={"message": "任务不存在"}).model_dump(), ensure_ascii=False)
            CRUDReviewTask.update_task_status(db, review_task.id, "processing")
            contract = await CRUDContract.get_contract_file(db, review_task.contract_id)
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

            # 分割合同内容
            chunks = split_text_by_length(contract_content, max_length=4000)
            global_index = 1
            for idx, chunk_content in enumerate(chunks):
                try:
                    # 构建审阅上下文
                    context = ""
                    if idx > 0:
                        context = f"这是第 {idx + 1} 个分块，前面已审阅 {idx} 个分块。"
                    # 执行审阅
                    modifications = await contract_review_service.review_contract(
                        chunk_content, review_task.stance, "", context
                    )
                    for j, modification in enumerate(modifications):
                        review_result=CRUDReviewResult.create_review_result(
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
            yield {
                "event": "end",
                "data": json.dumps(
                    ReviewTaskSSEResponse(
                        event="end",
                        data={
                            "type": "summary",
                            "summary": summary,
                            "suggestion": suggestion
                        }
                    ).model_dump(), ensure_ascii=False)
            }
    return  EventSourceResponse(
        event_generator()
    )



@router.get("/list", response_model=GenericResponse[ReviewTaskListResponse],summary="获取用户的审阅任务列表")
async def get_review_task_list(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """获取用户的审阅任务列表"""
    try:
        tasks = CRUDReviewTask.get_user_review_tasks(db, current_user.id, skip, limit)
        return GenericResponse(
            code=200,
            msg="获取任务列表成功",
            data=ReviewTaskListResponse(
                total=len(tasks),
                tasks=tasks
            )
        )
    except Exception as e:
        logger.error(f"获取任务列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")

@router.post("/review_task_detail", response_model=GenericResponse[ReviewTaskDetailResponse],summary="获取任务详情")
async def review_task_detail(
        task_id: int,
        current_user: User = Depends(get_current_user),
        db: DBSession = Depends(get_db)
):
    """获取审阅任务详情"""
    try:
        task = CRUDReviewTask.get_review_task(db, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="审阅任务不存在")

        return GenericResponse(
            code=200,
            msg="获取任务详情成功",
            data=task
        )
    except Exception as e:
        logger.error(f"获取任务详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务详情失败: {str(e)}")

@router.delete("/{task_id}", response_model=GenericResponse[dict])
async def delete_review_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """删除审阅任务"""
    try:
        # 验证任务权限
        review_task = CRUDReviewTask.get_review_task(db, task_id)
        if not review_task:
            raise HTTPException(status_code=404, detail="审阅任务不存在")
        
        if review_task.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权限删除此任务")
        
        # 删除任务
        success = CRUDReviewTask.delete_review_task(db, task_id)
        if not success:
            raise HTTPException(status_code=500, detail="删除任务失败")
        
        # 清理进度信息
        if task_id in review_progress:
            del review_progress[task_id]
        
        logger.info(f"用户 {current_user.id} 删除审阅任务 {task_id}")
        
        return GenericResponse(
            code=200,
            msg="删除任务成功",
            data={"task_id": task_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除审阅任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除审阅任务失败: {str(e)}")


async def execute_review_task(
    task_id: int,
    contract_id: int,
    stance: str,
    intensity: str,
    description: str,
    user_id: int
):
    """执行审阅任务的后台函数"""
    from app.core.dependencies import SessionLocal
    
    db = SessionLocal()
    try:
        logger.info(f"开始执行审阅任务 {task_id}")
        
        # 更新进度
        review_progress[task_id]["message"] = "正在获取合同文件..."
        
        # 获取合同文件
        contract = await CRUDContract.get_contract_file(db, contract_id)
        if not contract:
            raise Exception("合同文件不存在")
        
        # 更新进度
        review_progress[task_id]["message"] = "正在提取合同内容..."
        
        # 初始化MCP客户端和审阅服务
        mcp_client = MCPClient()
        await mcp_client.initialize()
        contract_review_service = ContractReviewService(mcp_client)
        
        # 提取合同内容
        file_ext = contract.file_path.split('.')[-1].lower()
        if file_ext == 'pdf':
            contract_content = await mcp_client.extract_pdf_document_content(contract.file_path)
        else:
            contract_content = await mcp_client.extract_document_content(contract.file_path)

        # 分割合同内容
        chunks = split_text_by_length(contract_content, max_length=4000)
        review_progress[task_id]["total_chunks"] = len(chunks)
        review_progress[task_id]["message"] = f"开始审阅，共 {len(chunks)} 个分块"
        
        all_modifications = []
        
        # 审阅每个分块
        for idx, chunk_content in enumerate(chunks):
            try:
                review_progress[task_id]["current_chunk"] = idx + 1
                review_progress[task_id]["message"] = f"正在审阅第 {idx + 1}/{len(chunks)} 个分块"
                
                # 构建审阅上下文
                context = ""
                if idx > 0:
                    context = f"这是第 {idx + 1} 个分块，前面已审阅 {idx} 个分块。"
                
                # 执行审阅
                modifications = await contract_review_service.review_contract(
                    chunk_content, stance, "", context
                )
                
                all_modifications.extend(modifications)
                # 将本chunk结果推送到流队列
                try:
                    q = stream_queues.get(task_id)
                    if q is not None:
                        pct = 0
                        if review_progress[task_id]["total_chunks"]:
                            pct = round(
                                review_progress[task_id]["current_chunk"] / review_progress[task_id]["total_chunks"] * 100, 1
                            )
                        await q.put({
                            "type": "chunk_result",
                            "chunk_index": idx + 1,
                            "total_chunks": len(chunks),
                            "percentage": pct,
                            "modifications": modifications,
                        })
                except Exception as _:
                    pass
                
                logger.info(f"任务 {task_id} 第 {idx + 1} 个分块审阅完成，发现 {len(modifications)} 个修改点")
                
            except Exception as e:
                logger.error(f"任务 {task_id} 第 {idx + 1} 个分块审阅失败: {e}")
                continue
        
        # 更新进度
        review_progress[task_id]["message"] = "正在保存审阅结果..."
        
        # 分析整体风险等级
        overall_risk = "低"
        if len(all_modifications) > 10:
            overall_risk = "高"
        elif len(all_modifications) > 5:
            overall_risk = "中"
        
        # 生成摘要和建议
        summary = f"共发现 {len(all_modifications)} 个潜在风险点，整体风险等级为 {overall_risk}。"
        suggestion = f"建议重点关注风险等级较高的条款，并根据 {stance} 立场进行相应调整。"
        
        # 保存审阅结果
        review_result = CRUDReviewTask.create_review_result(
            db, task_id, overall_risk, summary, suggestion
        )
        
        # 保存风险项
        for mod in all_modifications:
            CRUDReviewTask.create_risk_item(
                db,
                review_result.id,
                mod.get("original_content", ""),
                mod.get("position", "未知"),
                mod.get("risk_level", "未知"),
                mod.get("suggested_content", "")
            )
        
        # 更新任务状态为完成
        CRUDReviewTask.update_task_status(db, task_id, "completed")
        
        # 更新进度
        review_progress[task_id]["status"] = "completed"
        review_progress[task_id]["message"] = f"审阅完成，共发现 {len(all_modifications)} 个风险点"

        # 通知完成
        try:
            q = stream_queues.get(task_id)
            if q is not None:
                await q.put({"type": "completed"})
        except Exception:
            pass
        
        logger.info(f"审阅任务 {task_id} 执行完成")
        
    except Exception as e:
        logger.error(f"执行审阅任务 {task_id} 失败: {e}")
        review_progress[task_id]["status"] = "failed"
        review_progress[task_id]["message"] = f"审阅失败: {str(e)}"
        
        # 更新任务状态为失败
        CRUDReviewTask.update_task_status(db, task_id, "failed")
        # 通知失败
        try:
            q = stream_queues.get(task_id)
            if q is not None:
                await q.put({"type": "failed", "error": str(e)})
        except Exception:
            pass
        
    finally:
        db.close()
