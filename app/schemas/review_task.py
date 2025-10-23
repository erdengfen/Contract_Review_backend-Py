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
    stance: str = Field(..., description="审查立场（甲方/乙方）")
    intensity: str = Field(..., description="审查尺度（严格/标准/宽松）")
    description: Optional[str] = Field(None, description="审查需求描述")


class ReviewTaskResponse(BaseModel):
    """审阅任务响应"""
    id: int = Field(..., description="任务ID")
    contract_id: int = Field(..., description="所属文件ID")
    user_id: int = Field(..., description="发起用户ID")
    stance: str = Field(..., description="审查立场")
    intensity: str = Field(..., description="审查尺度")
    description: Optional[str] = Field(None, description="审查需求描述")
    status: str = Field(..., description="状态")
    created_at: datetime = Field(..., description="创建时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")


class ReviewResultResponse(BaseModel):
    """审阅结果响应"""
    id: int = Field(..., description="结果ID")
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


class ReviewProgressResponse(BaseModel):
    """审阅进度响应"""
    task_id: int = Field(..., description="任务ID")
    current_chunk: int = Field(..., description="当前分块")
    total_chunks: int = Field(..., description="总分块数")
    percentage: float = Field(..., description="完成百分比")
    status: str = Field(..., description="状态")
    message: str = Field(..., description="状态消息")


class ChatRequest(BaseModel):
    """合同问答请求"""
    contract_id: str = Field(..., description="合同ID")
    question: str = Field(..., description="用户问题")
