"""
API请求/响应模型
"""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class ChatRequest(BaseModel):
    message: Optional[str] = "审阅"
    session_id: str
    action: Optional[str] = "chat"  # chat, review, modify, export

class ChatResponse(BaseModel):
    response: str
    session_id: str
    action: str
    modifications: Optional[List[Dict[str, Any]]] = None
    modified_document_url: Optional[str] = None
    report_url: Optional[str] = None

class UploadResponse(BaseModel):
    success: bool
    message: str
    session_id: str
    document_id: str
