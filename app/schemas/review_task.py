"""
@Project ：Contract_Review_backend-Py 
@File    ：review_task.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/23 10:12 
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ReviewTaskCreateRequest(BaseModel):
    """创建审阅任务请求"""
    contract_id: int = Field(..., description="合同文件ID")
    session_id: int = Field(..., description="会话ID")
    stance: str = Field(..., description="审查立场（甲方/乙方）")
    intensity: str = Field(..., description="审查尺度（严格/标准/宽松）")
    description: Optional[str] = Field(None, description="审查需求描述")


class ReviewTaskResponse(BaseModel):
    """审阅任务响应"""
    id: int = Field(..., description="任务ID")
    session_id: int = Field(..., description="会话ID")
    contract_id: int = Field(..., description="所属文件ID")
    user_id: int = Field(..., description="发起用户ID")
    stance: str = Field(..., description="审查立场")
    intensity: str = Field(..., description="审查尺度")
    description: Optional[str] = Field(None, description="审查需求描述")
    status: str = Field(..., description="状态")
    created_at: datetime = Field(..., description="创建时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")




class ReviewTaskSSEResponse(BaseModel):
    """
    审查任务流式分块响应数据格式
    """
    event: Optional[str]=Field(...,description="事件类型")
    data:Optional[dict]=Field(...,description="数据")

class ReviewResultResponse(BaseModel):
    """审阅结果响应"""
    id: int = Field(..., description="结果ID")
    session_id: int = Field(..., description="会话ID")
    task_id: int = Field(..., description="任务ID")
    overall_risk: str = Field(..., description="整体风险等级")
    summary: str = Field(..., description="审阅摘要")
    suggestion: str = Field(..., description="建议")
    created_at: datetime = Field(..., description="创建时间")


class RiskItemResponse(BaseModel):
    """风险项响应"""
    id: int = Field(..., description="风险项ID")
    result_id: int = Field(..., description="结果ID")
    clause_text: str = Field(..., description="条款内容")
    risk_type: str = Field(..., description="风险类型")
    risk_level: str = Field(..., description="风险等级")
    suggestion: str = Field(..., description="建议")



class ReviewTaskListResponse(BaseModel):
    """审阅任务列表响应"""
    total: int = Field(..., description="总记录数")
    tasks: List[ReviewTaskResponse] = Field(..., description="任务列表")


class ReviewTaskDetailResponse(BaseModel):
    """审阅任务详情响应"""
    task: ReviewTaskResponse = Field(..., description="任务详情")
    results: List[ReviewResultResponse] = Field(..., description="结果列表")
    risk_items: List[RiskItemResponse] = Field(..., description="风险项列表")


class ChatRequest(BaseModel):
    """合同问答请求"""
    contract_id: str = Field(..., description="合同ID")
    question: str = Field(..., description="用户问题")
