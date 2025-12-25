"""
@Project ：Contract_Review_backend-Py 
@File    ：session.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/11/4 10:46 
"""
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List


class SessionResponse(BaseModel):
    """创建会话响应体"""
    session_id: int = Field(..., description="会话ID", alias="id")
    title: str = Field(..., description="会话主题")
    session_type: str = Field(..., description="会话类型")
    file_id: Optional[int] = Field(None, description="关联文件ID")
    created_at: Optional[datetime] = Field(..., description="创建时间")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )

class CreateSessionRequest(BaseModel):
    """创建会话请求体"""
    title: str = Field(..., description="会话主题")
    session_type: str = Field(..., description="会话类型")
    file_id: Optional[int] = Field(None, description="关联文件ID")

class ListSessionRequest(BaseModel):
    """查询会话列表请求体"""
    page: int = Field(..., description="页码")
    page_size: int = Field(..., description="每页数量")
    session_type: str = Field(..., description="会话类型")

class ReviewSessionResponse(BaseModel):
    """审阅类型list响应体内容"""
    session_id: int = Field(..., description="会话ID", alias="id")
    title: str = Field(..., description="会话主题")
    session_type: str = Field(..., description="会话类型")
    file_id: Optional[int] = Field(None, description="关联文件ID")
    created_at: Optional[datetime] = Field(..., description="创建时间")
    party_a: Optional[str] = Field(None, description="甲方信息")
    party_b: Optional[str] = Field(None, description="乙方信息")
    is_accepted: Optional[bool] = Field(False, description="是否已接受修订")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )

class ReviewSessionListResponse(BaseModel):
    """审阅类型会话列表响应体"""
    sessions: Optional[List[ReviewSessionResponse]] = Field(None, description="会话列表")
    total: int = Field(..., description="会话总数")

class CompareSessionResponse(BaseModel):
    """比对类型list响应体内容"""
    session_id: int = Field(..., description="会话ID", alias="id")
    title: str = Field(..., description="会话主题")
    session_type: str = Field(..., description="会话类型")
    created_at: Optional[datetime] = Field(..., description="创建时间")
    file_id: Optional[int] = Field(None, description="合同1关联文件ID")
    party_a: Optional[str] = Field(None, description="合同1甲方信息")
    party_b: Optional[str] = Field(None, description="合同1乙方信息")
    is_accepted: Optional[bool] = Field(False, description="合同1是否已接受修订")
    file_id_2: Optional[int] = Field(None, description="合同2关联文件ID")
    party_a_2: Optional[str] = Field(None, description="合同2甲方信息")
    party_b_2: Optional[str] = Field(None, description="合同2乙方信息")
    is_accepted_2: Optional[bool] = Field(False, description="合同2是否已接受修订")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )

class CompareSessionListResponse(BaseModel):
    """比对类型会话列表响应体"""
    sessions: Optional[List[CompareSessionResponse]] = Field(None, description="会话列表")
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
