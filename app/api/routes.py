"""
API路由
"""
import uuid
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse

from .models import ChatRequest, ChatResponse, UploadResponse
from ..services.chat_service import ChatService
from ..utils.mcp_client import MCPClient
from ..core.config import UPLOAD_DIR

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter()

# 全局服务实例（将在main.py中初始化）
chat_service: ChatService = None
mcp_client: MCPClient = None

async def init_services():
    """初始化服务"""
    global chat_service, mcp_client
    
    mcp_client = MCPClient()
    
    # 初始化MCP客户端
    await mcp_client.initialize()
    
    # 这里需要导入服务类
    from ..services.contract_review import ContractReviewService
    from ..services.document_processor import DocumentProcessorService
    
    contract_review_service = ContractReviewService(mcp_client)
    document_processor_service = DocumentProcessorService(mcp_client)
    
    chat_service = ChatService(mcp_client, contract_review_service, document_processor_service)

@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    session_id: str = Form(None)
):
    """上传合同文档"""
    try:
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # 检查文件类型
        if not file.filename.endswith('.docx'):
            raise HTTPException(status_code=400, detail="只支持.docx格式的文件")
        
        # 保存文件（使用绝对路径，确保 MCP 服务器可访问）
        filename = f"{session_id}_{file.filename}"
        file_path = (Path(UPLOAD_DIR) / filename).resolve()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # 更新会话
        session = chat_service.get_or_create_session(session_id)
        session["contract_path"] = str(file_path)
        session["document_id"] = filename
        
        return UploadResponse(
            success=True,
            message="文件上传成功",
            session_id=session_id,
            document_id=filename
        )
        
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

@router.post("/chat", response_model=ChatResponse)
async def chat_with_assistant(request: ChatRequest):
    """与助手对话"""
    try:
        if not request.session_id:
            request.session_id = str(uuid.uuid4())
        
        result = await chat_service.process_message(
            request.message, 
            request.session_id, 
            request.action
        )
        
        return ChatResponse(**result)
        
    except Exception as e:
        logger.error(f"聊天处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"聊天处理失败: {str(e)}")

@router.get("/download/{session_id}/{file_type}")
async def download_file(session_id: str, file_type: str):
    """下载文件"""
    try:
        session = chat_service.get_or_create_session(session_id)
        
        if file_type == "modified":
            file_path = session.get("modified_contract_path")
            if not file_path or not Path(file_path).exists():
                raise HTTPException(status_code=404, detail="修改后的文档不存在")
            return FileResponse(
                file_path, 
                filename=f"modified_contract_{session_id}.docx",
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )


        elif file_type == "report":
            file_path = session.get("report_path")
            if not file_path or not Path(file_path).exists():
                raise HTTPException(status_code=404, detail="报告不存在")
            return FileResponse(
                file_path, 
                filename=f"contract_report_{session_id}.md",
                media_type="text/markdown"
            )
        
        else:
            raise HTTPException(status_code=400, detail="不支持的文件类型")
            
    except Exception as e:
        logger.error(f"文件下载失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件下载失败: {str(e)}")

@router.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """获取会话信息"""
    try:
        session = chat_service.get_or_create_session(session_id)
        return {
            "session_id": session_id,
            "has_contract": bool(session.get("contract_path")),
            "modifications_count": len(session.get("modifications", [])),
            "has_modified_document": bool(session.get("modified_contract_path")),
            "has_report": bool(session.get("report_path")),
            "created_at": session.get("created_at")
        }
    except Exception as e:
        logger.error(f"获取会话信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取会话信息失败: {str(e)}")

@router.get("/health")
async def health_check():
    """健康检查"""
    from datetime import datetime
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
