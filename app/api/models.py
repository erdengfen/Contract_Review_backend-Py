"""
API请求/响应模型
"""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class ChatRequest(BaseModel):
    message: Optional[str] = "审阅"
    session_id: str
    action: Optional[str] = "chat"  # chat, review, modify, export
    role: Optional[str] = None
    contract_type: Optional[str] = None #合同类型，暂时包括:服务合同service，买卖合同sales

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
    party_a: Optional[str] = None #甲方名称
    party_b: Optional[str] = None #乙方名称
