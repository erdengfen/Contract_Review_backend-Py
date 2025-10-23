"""
@Project ：Contract_Review_backend-Py 
@File    ：chat.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/23 10:32 
"""
from datetime import datetime

from pydantic import BaseModel, Field
from typing import Optional, List


class CreateSessionRequest(BaseModel):
    """创建会话请求体"""
    title: str = Field(..., description="会话主题")
    contract_id: Optional[int] = Field(None, description="关联的合同文件ID（可选）")
    session_type: Optional[str] = Field(..., description="会话类型")

class SessionResponse(BaseModel):
    """创建会话响应体"""
    session_id: int = Field(..., description="会话ID")
    title: str = Field(..., description="会话主题")
    session_type: str = Field(..., description="会话类型")
    contract_id: Optional[int] = Field(None, description="关联文件ID")
    created_at: str = Field(..., description="创建时间")



class SessionListResponse(BaseModel):
    total: int = Field(..., description="总记录数")
    sessions: List[SessionResponse] = Field(..., description="会话记录列表")


class UpdateSessionTitleRequest(BaseModel):
    new_title: str = Field(..., description="新的会话标题")

# ------message-------------------------

class MessageCreateRequest(BaseModel):
    session_id: int = Field(..., description="会话ID")
    role: str = Field(..., description="角色（user/assistant/system）")
    content: str = Field(..., description="消息内容")
    parent_id: Optional[int] = Field(None, description="父消息ID")

class MessageUpdateRequest(BaseModel):
    content: str = Field(..., description="更新后的消息内容")

class MessageResponse(BaseModel):
    id: int = Field(..., description="消息ID")
    session_id: int = Field(..., description="会话ID")
    role: str = Field(..., description="角色（user/assistant/system）")
    content: str = Field(..., description="消息内容")
    parent_id: Optional[int] = Field(None, description="父消息ID")
    message_index: Optional[int] = Field(None, description="消息索引")
    created_at: datetime = Field(..., description="创建时间")
