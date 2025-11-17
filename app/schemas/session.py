"""
@Project ：Contract_Review_backend-Py 
@File    ：session.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/11/4 10:46 
"""
from pydantic import BaseModel, Field
from typing import Optional, List


class SessionResponse(BaseModel):
    """创建会话响应体"""
    session_id: int = Field(..., description="会话ID")
    title: str = Field(..., description="会话主题")
    session_type: str = Field(..., description="会话类型")
    file_id: Optional[int] = Field(None, description="关联文件ID")
    created_at: str = Field(..., description="创建时间")

class CreateSessionRequest(BaseModel):
    """创建会话请求体"""
    title: str = Field(..., description="会话主题")
    session_type: str = Field(..., description="会话类型")
    file_id: Optional[int] = Field(None, description="关联文件ID")

class ListSessionRequest(BaseModel):
    """查询会话列表请求体"""
    page: int = Field(..., description="页码")
    page_size: int = Field(..., description="每页数量")
    session_type: Optional[str] = Field(None, description="会话类型")


class SessionListResponse(BaseModel):
    """会话列表响应体"""
    data: Optional[List[SessionResponse]] = Field(None, description="会话列表")
    total: int = Field(..., description="会话总数")


class UpdateSessionTitleRequest(BaseModel):
    """修改会话标题请求体"""
    session_id: int = Field(..., description="会话ID")
    new_title: str = Field(..., description="新的会话标题")


class DeleteSessionRequest(BaseModel):
    """删除会话请求体"""
    session_id: int = Field(..., description="会话ID")



class SessionHistoryDetailRequest(BaseModel):
    """获取会话历史记录请求体"""
    session_id: int = Field(..., description="会话ID")



class ChatSessionHistoryDetail(BaseModel):
    """获取聊天会话历史记录请求体"""
    pass

class ReviewSessionHistoryDetail(BaseModel):
    """获取审阅会话历史记录请求体"""
    pass

class SessionHistoryDetailResponse(BaseModel):
    """会话历史记录响应体"""
    session_id: int = Field(..., description="会话ID")
    title: str = Field(..., description="会话主题")
    session_type: str = Field(..., description="会话类型")
    file_id: Optional[int] = Field(None, description="关联文件ID")
    created_at: str = Field(..., description="创建时间")
    messages: Optional[List[dict]] = Field(None, description="消息记录")
