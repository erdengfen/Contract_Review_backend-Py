from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime




class ChatRequest(BaseModel):
    """
    合同聊天请求
    """
    session_id: Optional[int] = Field(None, description="会话ID（可选，用于继续会话）")
    content: Optional[str] = Field(None, description="消息内容（可选，用于创建消息）")
    parent_id: Optional[int] = Field(None, description="父消息ID（可选，用于多轮或修正）")  

class ChatMessageResponse(BaseModel):
    """
    合同聊天消息响应
    """
    id: int
    session_id: int
    role: str
    content: str
    parent_id: Optional[int]
    message_index: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True

class ChatSessionResponse(BaseModel):
    """
    合同聊天会话响应
    """
    session_id: int
    title: str
    messages: List[ChatMessageResponse]

    class Config:
        from_attributes = True


class CreateSessionRequest(BaseModel):
    """
    创建会话请求
    """
    contract_id: int
    user_id: int
    title: Optional[str] = None  


class UpdateSessionTitleRequest(BaseModel):
    """
    更新会话标题请求
    """
    title: str


class SessionListResponse(BaseModel):
    """
    会话列表响应项
    """
    session_id: int
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int

    class Config:
        from_attributes = True