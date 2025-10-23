"""
@Project ：Contract_Review_backend-Py 
@File    ：review_task.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/22 14:13 
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session as DBSession

from app.middlewares.auth import get_current_user
from app.schemas.base import GenericResponse
from app.schemas.review_task import (
    ReviewTaskCreateRequest, 
    ReviewTaskResponse, 
    ReviewResultResponse,
    RiskItemResponse,
    ReviewTaskListResponse,
    ReviewProgressResponse
)
from app.curd.review_task import CRUDReviewTask
from app.curd.contract_file import CRUDContract
from app.core.dependencies import get_db
from app.models.user import User
from app.services.contract_review import ContractReviewService
from app.utils.mcp_client import MCPClient
from app.utils.content_slicer import split_text_by_length

logger = logging.getLogger(__name__)

router = APIRouter(tags=["合同审阅"])
"""
合同审阅相关接口
"""

# 全局变量存储审阅进度
review_progress = {}


@router.post("/create", response_model=GenericResponse[ReviewTaskResponse])
async def create_review_task(
    request: ReviewTaskCreateRequest,
    current_user: User = Depends(get_current_user),
    current_session: DBSession = Depends(get_db),


    db: DBSession = Depends(get_db)
):
    """创建审阅任务"""
    try:
        # 验证合同文件是否存在
        contract = await CRUDContract.get_contract_file(db, request.contract_id)
        if not contract:
            raise HTTPException(status_code=404, detail="合同文件不存在")
        
        # 创建审阅任务
        review_task = CRUDReviewTask.create_review_task(db, current_user.id, request)
        
        logger.info(f"用户 {current_user.id} 创建审阅任务 {review_task.id}")
        
        return GenericResponse(
            code=200,
            msg="审阅任务创建成功",
            data=ReviewTaskResponse(
                id=review_task.id,
                contract_id=review_task.contract_id,
                user_id=review_task.user_id,
                stance=review_task.stance,
                intensity=review_task.intensity,
                description=review_task.description,
                status=review_task.status,
                created_at=review_task.created_at,
                completed_at=review_task.completed_at
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建审阅任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建审阅任务失败: {str(e)}")


@router.post("/start/{task_id}", response_model=GenericResponse[dict])
async def start_review_task(
    task_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """开始执行审阅任务"""
    try:
        # 获取审阅任务
        review_task = CRUDReviewTask.get_review_task(db, task_id)
        if not review_task:
            raise HTTPException(status_code=404, detail="审阅任务不存在")
        
        if review_task.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权限访问此任务")
        
        if review_task.status != "pending":
            raise HTTPException(status_code=400, detail="任务状态不允许开始审阅")
        
        # 更新任务状态为进行中
        CRUDReviewTask.update_task_status(db, task_id, "processing")
        
        # 初始化审阅进度
        review_progress[task_id] = {
            "current_chunk": 0,
            "total_chunks": 0,
            "status": "processing",
            "message": "正在准备审阅..."
        }
        
        # 在后台执行审阅任务
        background_tasks.add_task(
            execute_review_task, 
            task_id, 
            review_task.contract_id,
            review_task.stance,
            review_task.intensity,
            review_task.description,
            current_user.id
        )
        
        logger.info(f"开始执行审阅任务 {task_id}")
        
        return GenericResponse(
            code=200,
            msg="审阅任务已开始执行",
            data={"task_id": task_id, "status": "processing"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"开始审阅任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"开始审阅任务失败: {str(e)}")


@router.get("/progress/{task_id}", response_model=GenericResponse[ReviewProgressResponse])
async def get_review_progress(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """获取审阅进度"""
    try:
        # 验证任务权限
        review_task = CRUDReviewTask.get_review_task(db, task_id)
        if not review_task:
            raise HTTPException(status_code=404, detail="审阅任务不存在")
        
        if review_task.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权限访问此任务")
        
        # 获取进度信息
        progress = review_progress.get(task_id, {
            "current_chunk": 0,
            "total_chunks": 0,
            "status": "unknown",
            "message": "未知状态"
        })
        
        percentage = 0
        if progress["total_chunks"] > 0:
            percentage = round((progress["current_chunk"] / progress["total_chunks"]) * 100, 1)
        
        return GenericResponse(
            code=200,
            msg="获取进度成功",
            data=ReviewProgressResponse(
                task_id=task_id,
                current_chunk=progress["current_chunk"],
                total_chunks=progress["total_chunks"],
                percentage=percentage,
                status=progress["status"],
                message=progress["message"]
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取审阅进度失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取审阅进度失败: {str(e)}")


@router.get("/result/{task_id}", response_model=GenericResponse[dict])
async def get_review_result(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """获取审阅结果"""
    try:
        # 验证任务权限
        review_task = CRUDReviewTask.get_review_task(db, task_id)
        if not review_task:
            raise HTTPException(status_code=404, detail="审阅任务不存在")
        
        if review_task.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权限访问此任务")
        
        if review_task.status != "completed":
            raise HTTPException(status_code=400, detail="审阅任务尚未完成")
        
        # 获取审阅结果
        review_result = CRUDReviewTask.get_review_result(db, task_id)
        if not review_result:
            raise HTTPException(status_code=404, detail="审阅结果不存在")
        
        # 获取风险项列表
        risk_items = CRUDReviewTask.get_risk_items(db, review_result.id)
        
        return GenericResponse(
            code=200,
            msg="获取审阅结果成功",
            data={
                "task": ReviewTaskResponse(
                    id=review_task.id,
                    contract_id=review_task.contract_id,
                    user_id=review_task.user_id,
                    stance=review_task.stance,
                    intensity=review_task.intensity,
                    description=review_task.description,
                    status=review_task.status,
                    created_at=review_task.created_at,
                    completed_at=review_task.completed_at
                ),
                "result": ReviewResultResponse(
                    id=review_result.id,
                    task_id=review_result.task_id,
                    overall_risk=review_result.overall_risk,
                    summary=review_result.summary,
                    suggestion=review_result.suggestion,
                    created_at=review_result.created_at
                ),
                "risk_items": [
                    RiskItemResponse(
                        id=item.id,
                        result_id=item.result_id,
                        clause_text=item.clause_text,
                        risk_type=item.risk_type,
                        risk_level=item.risk_level,
                        suggestion=item.suggestion
                    ) for item in risk_items
                ]
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取审阅结果失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取审阅结果失败: {str(e)}")


@router.get("/list", response_model=GenericResponse[ReviewTaskListResponse])
async def get_review_task_list(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """获取用户的审阅任务列表"""
    try:
        tasks = CRUDReviewTask.get_user_review_tasks(db, current_user.id, skip, limit)
        
        task_responses = [
            ReviewTaskResponse(
                id=task.id,
                contract_id=task.contract_id,
                user_id=task.user_id,
                stance=task.stance,
                intensity=task.intensity,
                description=task.description,
                status=task.status,
                created_at=task.created_at,
                completed_at=task.completed_at
            ) for task in tasks
        ]
        
        return GenericResponse(
            code=200,
            msg="获取任务列表成功",
            data=ReviewTaskListResponse(
                total=len(task_responses),
                tasks=task_responses
            )
        )
        
    except Exception as e:
        logger.error(f"获取任务列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")


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
        
        logger.info(f"审阅任务 {task_id} 执行完成")
        
    except Exception as e:
        logger.error(f"执行审阅任务 {task_id} 失败: {e}")
        review_progress[task_id]["status"] = "failed"
        review_progress[task_id]["message"] = f"审阅失败: {str(e)}"
        
        # 更新任务状态为失败
        CRUDReviewTask.update_task_status(db, task_id, "failed")
        
    finally:
        db.close()
