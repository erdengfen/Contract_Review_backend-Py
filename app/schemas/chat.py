"""
@Project ：Contract_Review_backend-Py 
@File    ：chat.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/23 10:32 
"""

from pydantic import BaseModel, Field
from typing import Optional

class ChatRequest(BaseModel):
    contract_id: Optional[int] = Field(None, description="关联合同ID（可选）")
    title: Optional[str] = Field(None, description="会话标题（可选）")
    message: Optional[str] = Field(None, description="初始消息（可选）")

class ChatResponse(BaseModel):
    session_id: int
    title: str
    contract_id: Optional[int] = None
    created_at: str