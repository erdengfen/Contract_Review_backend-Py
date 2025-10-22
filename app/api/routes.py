"""
API路由
"""
import uuid
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from starlette.responses import StreamingResponse

from .models import ChatRequest, ChatResponse, UploadResponse
from ..services.chat_service import ChatService
from ..services.enhanced_memory_service import EnhancedMemoryService
from ..utils.mcp_client import MCPClient
from ..core.config import UPLOAD_DIR
from ..core.database import DatabaseManager
import json
from ..utils.contract_parser import extract_parties_with_llm

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter()

# 全局服务实例（将在main.py中初始化）
chat_service: ChatService = None
mcp_client: MCPClient = None
memory_service: EnhancedMemoryService = None

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
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # 检查文件类型
        allowed_files = ('.docx','.pdf')
        if not file.filename.lower().endswith(allowed_files):
            raise HTTPException(status_code=400, detail="只支持.docx或.pdf格式的文件")
        
        # 保存文件（使用用户ID和会话ID确保隔离）
        filename = f"{user_id}_{session_id}_{file.filename}"
        file_path = (Path(UPLOAD_DIR) / filename).resolve()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # 分析甲乙方
        parties = await extract_parties_with_llm(str(file_path), chat_service.llm)
        party_a = parties["party_a"]
        party_b = parties["party_b"]
        
        # 更新会话（使用增强记忆服务）
        await memory_service.update_user_session(user_id, session_id, {
            "contract_path": str(file_path),
            "document_id": filename,
            "party_a": party_a,
            "party_b": party_b
        })

        return UploadResponse(
            success=True,
            message="文件上传成功",
            session_id=session_id,
            document_id=filename,
            party_a=party_a,
            party_b=party_b
        )
        
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

@router.post("/chat", response_model=ChatResponse)
async def chat_with_assistant(request: ChatRequest):
    """与助手对话（支持多用户）"""
    try:
        if not request.session_id:
            request.session_id = str(uuid.uuid4())
        
        async def event_generator():
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

        return StreamingResponse(event_generator(), media_type="text/event-stream")
        
    except Exception as e:
        logger.error(f"聊天处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"聊天处理失败: {str(e)}")

@router.get("/download/{user_id}/{session_id}/{file_type}")
async def download_file(user_id: str, session_id: str, file_type: str):
    """下载文件（支持多用户）"""
    try:
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
            raise HTTPException(status_code=400, detail="不支持的文件类型")
            
    except Exception as e:
        logger.error(f"文件下载失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件下载失败: {str(e)}")

@router.get("/session/{user_id}/{session_id}")
async def get_session_info(user_id: str, session_id: str):
    """获取会话信息（支持多用户）"""
    try:
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
            "updated_at": session.get("updated_at")
        }
    except Exception as e:
        logger.error(f"获取会话信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取会话信息失败: {str(e)}")

@router.get("/sessions/{user_id}")
async def get_user_sessions(user_id: str):
    """获取用户的所有会话"""
    try:
        sessions = await memory_service.get_user_active_sessions(user_id)
        return {
            "user_id": user_id,
            "sessions": sessions,
            "total_count": len(sessions)
        }
    except Exception as e:
        logger.error(f"获取用户会话列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取用户会话列表失败: {str(e)}")

@router.delete("/session/{user_id}/{session_id}")
async def delete_session(user_id: str, session_id: str):
    """删除会话"""
    try:
        success = await memory_service.delete_user_session(user_id, session_id)
        if success:
            return {"message": "会话删除成功", "success": True}
        else:
            raise HTTPException(status_code=500, detail="会话删除失败")
    except Exception as e:
        logger.error(f"删除会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除会话失败: {str(e)}")

@router.get("/health")
async def health_check():
    """健康检查"""
    from datetime import datetime
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
