"""
合同审阅系统 API路由

主要功能：
1. 文件上传和管理
2. 聊天对话和合同审阅
3. 会话管理（创建、查询、删除）
4. 文件下载（修改后的合同、审阅报告）
5. 用户会话统计

支持多用户并发，每个用户的数据完全隔离。
"""
import uuid
import logging
from distutils.command.upload import upload
from http.client import responses
from os.path import split
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from starlette.responses import StreamingResponse
from typing import List

from .models import ChatRequest, ChatResponse, UploadResponse
from ..services.chat_service import ChatService
from ..services.enhanced_memory_service import EnhancedMemoryService
from ..utils.mcp_client import MCPClient
from ..core.config import UPLOAD_DIR
from ..core.database import DatabaseManager
import json
from ..utils.contract_parser import extract_parties_with_llm
from ..config.config import settings

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter()

# 全局服务实例（将在main.py中初始化）
chat_service: ChatService = None
mcp_client: MCPClient = None
memory_service: EnhancedMemoryService = None

# 工具函数
def validate_user_id(user_id: str) -> bool:
    """验证用户ID格式"""
    return user_id and user_id.strip() != ""

def validate_session_id(session_id: str) -> bool:
    """验证会话ID格式"""
    return session_id and session_id.strip() != ""

def format_error_response(message: str, status_code: int = 400) -> HTTPException:
    """格式化错误响应"""
    return HTTPException(status_code=status_code, detail=message)

async def init_services():
    """初始化服务"""
    global chat_service, mcp_client, memory_service
    
    # 初始化数据库
    db_manager = DatabaseManager()
    
    # 初始化Redis和记忆服务
    memory_service = EnhancedMemoryService(db_manager)
    
    # 初始化MCP客户端
    mcp_client = MCPClient()
    await mcp_client.initialize()
    
    # 初始化其他服务
    from ..services.contract_review import ContractReviewService
    from ..services.document_processor import DocumentProcessorService
    
    contract_review_service = ContractReviewService(mcp_client)
    document_processor_service = DocumentProcessorService(mcp_client)
    chat_service = ChatService(mcp_client, contract_review_service, document_processor_service, memory_service)

@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    session_id: str = Form(None)
):
    """上传合同文档（支持多用户）"""
    try:
        # 参数验证
        if not validate_user_id(user_id):
            raise format_error_response("用户ID不能为空")
        if not file.filename:
            raise format_error_response("文件名不能为空")
        
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # 检查文件类型
        allowed_files = ('.docx','.pdf')
        if not file.filename.lower().endswith(allowed_files):
            raise HTTPException(status_code=400, detail="只支持.docx或.pdf格式的文件")
        
        # 检查文件大小（限制为50MB）
        file_size = 0
        content = await file.read()
        file_size = len(content)
        if file_size > 50 * 1024 * 1024:  # 50MB
            raise HTTPException(status_code=400, detail="文件大小不能超过50MB")
        
        # 保存文件（使用用户ID和会话ID确保隔离）
        filename = f"{user_id}_{session_id}_{file.filename}"
        file_path = (Path(UPLOAD_DIR) / filename).resolve()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, "wb") as buffer:
            buffer.write(content)

        # 分析甲乙方
        try:
            parties = await extract_parties_with_llm(str(file_path), chat_service.llm)
            party_a = parties.get("party_a", "未知")
            party_b = parties.get("party_b", "未知")
        except Exception as e:
            logger.warning(f"分析甲乙方失败: {e}")
            party_a = "未知"
            party_b = "未知"
        
        # 更新会话（使用增强记忆服务）
        await memory_service.update_user_session(user_id, session_id, {
            "contract_path": str(file_path),
            "document_id": filename,
            "party_a": party_a,
            "party_b": party_b
        })

        file_url = f"http://{settings.server.host}:{settings.server.port}/{UPLOAD_DIR}/{filename}"

        logger.info(f"文件上传成功: {user_id}/{session_id}, 文件: {filename}")
        return UploadResponse(
            success=True,
            message="文件上传成功",
            user_id=user_id,
            session_id=session_id,
            file_url=file_url,
            document_id=filename,
            party_a=party_a,
            party_b=party_b
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

@router.post("/chat", response_model=ChatResponse)
async def chat_with_assistant(request: ChatRequest):
    """与助手对话（支持多用户）"""
    try:
        # 参数验证
        if not validate_user_id(request.user_id):
            raise format_error_response("用户ID不能为空")
        if not request.message or request.message.strip() == "":
            raise format_error_response("消息内容不能为空")
        
        if not request.session_id:
            request.session_id = str(uuid.uuid4())
        
        # 检查服务是否可用
        if not chat_service:
            raise HTTPException(status_code=503, detail="聊天服务不可用，请稍后重试")
        
        async def event_generator():
            try:
                async for chunk in chat_service.process_message(
                    request.message,
                    request.user_id,
                    request.session_id,
                    request.action,
                    request.role,
                    request.contract_type
                ):
                    # SSE 格式：data: <JSON字符串>\n\n
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            except Exception as e:
                logger.error(f"聊天处理过程中出错: {e}")
                error_chunk = {
                    "type": "error",
                    "message": f"处理消息时出错: {str(e)}",
                    "user_id": request.user_id,
                    "session_id": request.session_id
                }
                yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"

        logger.info(f"开始处理聊天请求: {request.user_id}/{request.session_id}")
        return StreamingResponse(event_generator(), media_type="text/event-stream")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"聊天处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"聊天处理失败: {str(e)}")

@router.get("/download/{user_id}/{session_id}/{file_type}")
async def download_file(user_id: str, session_id: str, file_type: str):
    """下载文件（支持多用户）"""
    try:
        # 参数验证
        if not user_id or user_id.strip() == "":
            raise HTTPException(status_code=400, detail="用户ID不能为空")
        if not session_id or session_id.strip() == "":
            raise HTTPException(status_code=400, detail="会话ID不能为空")
        if not file_type or file_type.strip() == "":
            raise HTTPException(status_code=400, detail="文件类型不能为空")
        
        session = await memory_service.get_or_create_user_session(user_id, session_id)
        
        if file_type == "modified":
            file_path = session.get("modified_contract_path")
            if not file_path or not Path(file_path).exists():
                raise HTTPException(status_code=404, detail="修改后的文档不存在")
            return FileResponse(
                file_path, 
                filename=f"modified_contract_{user_id}_{session_id}.docx",
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

        elif file_type == "report":
            file_path = session.get("report_path")
            if not file_path or not Path(file_path).exists():
                raise HTTPException(status_code=404, detail="报告不存在")
            return FileResponse(
                file_path, 
                filename=f"contract_report_{user_id}_{session_id}.md",
                media_type="text/markdown"
            )
        
        else:
            raise HTTPException(status_code=400, detail="不支持的文件类型，支持的类型: modified, report")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件下载失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件下载失败: {str(e)}")

@router.get("/session/{user_id}/{session_id}")
async def get_session_info(user_id: str, session_id: str):
    """获取会话信息（支持多用户）"""
    try:
        # 参数验证
        if not user_id or user_id.strip() == "":
            raise HTTPException(status_code=400, detail="用户ID不能为空")
        if not session_id or session_id.strip() == "":
            raise HTTPException(status_code=400, detail="会话ID不能为空")
        
        session = await memory_service.get_or_create_user_session(user_id, session_id)
        
        return {
            "user_id": user_id,
            "session_id": session_id,
            "has_contract": bool(session.get("contract_path")),
            "modifications_count": len(session.get("modifications", [])),
            "has_modified_document": bool(session.get("modified_contract_path")),
            "has_report": bool(session.get("report_path")),
            "party_a": session.get("party_a", ""),
            "party_b": session.get("party_b", ""),
            "created_at": session.get("created_at"),
            "updated_at": session.get("updated_at"),
            "success": True
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取会话信息失败: {str(e)}")

@router.get("/sessions/{user_id}")
async def get_user_sessions(user_id: str):
    """获取用户的所有会话（历史合同审查记录列表）"""
    try:
        if not user_id or user_id.strip() == "":
            raise HTTPException(status_code=400, detail="用户ID不能为空")
        
        sessions = await memory_service.get_user_active_sessions(user_id)
        
        # 格式化会话数据，使其更像ChatGPT的会话列表
        formatted_sessions = []
        for session in sessions:
            formatted_session = {
                "session_id": session["session_id"],
                "title": f"{session.get('party_a', '未知')} vs {session.get('party_b', '未知')}",
                "created_at": session["created_at"],
                "updated_at": session["updated_at"],
                "has_contract": session["has_contract"],
                "modifications_count": session["modifications_count"],
                "party_a": session.get("party_a", ""),
                "party_b": session.get("party_b", ""),
                "status": "completed" if session["has_contract"] and session["modifications_count"] > 0 else "in_progress"
            }
            formatted_sessions.append(formatted_session)
        
        return {
            "user_id": user_id,
            "sessions": formatted_sessions,
            "total_count": len(formatted_sessions),
            "success": True
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户会话列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取用户会话列表失败: {str(e)}")

@router.delete("/session/{user_id}/{session_id}")
async def delete_session(user_id: str, session_id: str):
    """删除会话（支持多用户隔离）"""
    try:
        # 参数验证
        if not user_id or user_id.strip() == "":
            raise HTTPException(status_code=400, detail="用户ID不能为空")
        if not session_id or session_id.strip() == "":
            raise HTTPException(status_code=400, detail="会话ID不能为空")
        
        # 检查会话是否存在
        session = await memory_service.get_or_create_user_session(user_id, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 删除会话
        success = await memory_service.delete_user_session(user_id, session_id)
        if success:
            logger.info(f"会话删除成功: {user_id}/{session_id}")
            return {
                "message": "会话删除成功", 
                "success": True,
                "user_id": user_id,
                "session_id": session_id
            }
        else:
            raise HTTPException(status_code=500, detail="会话删除失败")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除会话失败: {str(e)}")

# @router.delete("/sessions/{user_id}/batch")
# async def batch_delete_sessions(user_id: str, session_ids: List[str]):
#     """批量删除会话"""
#     try:
#         if not user_id or user_id.strip() == "":
#             raise HTTPException(status_code=400, detail="用户ID不能为空")
#         if not session_ids:
#             raise HTTPException(status_code=400, detail="会话ID列表不能为空")
#
#         deleted_count = 0
#         failed_sessions = []
#
#         for session_id in session_ids:
#             try:
#                 success = await memory_service.delete_user_session(user_id, session_id)
#                 if success:
#                     deleted_count += 1
#                 else:
#                     failed_sessions.append(session_id)
#             except Exception as e:
#                 logger.error(f"删除会话失败 {session_id}: {e}")
#                 failed_sessions.append(session_id)
#
#         return {
#             "message": f"批量删除完成，成功删除{deleted_count}个会话",
#             "success": True,
#             "deleted_count": deleted_count,
#             "failed_sessions": failed_sessions,
#             "total_requested": len(session_ids)
#         }
#
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"批量删除会话失败: {e}")
#         raise HTTPException(status_code=500, detail=f"批量删除会话失败: {str(e)}")

# @router.get("/sessions/{user_id}/stats")
# async def get_user_session_stats(user_id: str):
#     """获取用户会话统计信息"""
#     try:
#         if not user_id or user_id.strip() == "":
#             raise HTTPException(status_code=400, detail="用户ID不能为空")
#
#         sessions = await memory_service.get_user_active_sessions(user_id)
#
#         # 统计信息
#         total_sessions = len(sessions)
#         completed_sessions = sum(1 for s in sessions if s.get("has_contract") and s.get("modifications_count", 0) > 0)
#         in_progress_sessions = total_sessions - completed_sessions
#         total_modifications = sum(s.get("modifications_count", 0) for s in sessions)
#
#         # 按月份统计
#         from collections import defaultdict
#         monthly_stats = defaultdict(int)
#         for session in sessions:
#             try:
#                 from datetime import datetime
#                 created_date = datetime.fromisoformat(session["created_at"].replace('Z', '+00:00'))
#                 month_key = created_date.strftime("%Y-%m")
#                 monthly_stats[month_key] += 1
#             except:
#                 continue
#
#         return {
#             "user_id": user_id,
#             "total_sessions": total_sessions,
#             "completed_sessions": completed_sessions,
#             "in_progress_sessions": in_progress_sessions,
#             "total_modifications": total_modifications,
#             "monthly_stats": dict(monthly_stats),
#             "success": True
#         }
#
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"获取用户会话统计失败: {e}")
#         raise HTTPException(status_code=500, detail=f"获取用户会话统计失败: {str(e)}")

@router.get("/health")
async def health_check():
    """健康检查"""
    from datetime import datetime
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
