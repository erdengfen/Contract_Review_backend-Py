"""Agent 契约通用结构。

本文件定义 backend 调用 agent 能力时共享的快照、正文引用和错误结构。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AgentContractModel(BaseModel):
    """Agent 契约基类，统一禁止未设计字段进入业务契约。"""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class SessionSnapshot(AgentContractModel):
    """会话快照，来源于旧版会话表和当前接口中的会话上下文。"""

    session_id: int | None = Field(None, description="会话ID。")
    file_id: int | None = Field(None, description="会话关联的合同文件ID。")
    user_id: int | None = Field(None, description="会话发起用户ID，聊天未登录场景可为空。")
    title: str | None = Field(None, description="会话标题。")
    session_type: str | None = Field(None, description="会话类型。")
    created_at: datetime | None = Field(None, description="会话创建时间。")
    updated_at: datetime | None = Field(None, description="会话更新时间。")


class ContractFileSnapshot(AgentContractModel):
    """合同文件快照，承接旧版合同文件表的完整业务字段。"""

    file_id: int | None = Field(None, description="合同文件ID。")
    user_id: int | None = Field(None, description="上传用户ID。")
    type: str | None = Field(None, description="合同文件业务类型，如 uploaded 或 parsed。")
    title: str | None = Field(None, description="合同标题或上传文件名。")
    file_path: str | None = Field(None, description="合同原文件保存路径。")
    file_type: str | None = Field(None, description="合同文件类型。")
    upload_time: datetime | None = Field(None, description="上传时间。")
    status: str | None = Field(None, description="合同文件状态。")
    party_a: str | None = Field(None, description="甲方名称。")
    party_b: str | None = Field(None, description="乙方名称。")
    amount: float | None = Field(None, description="合同金额。")
    is_accepted: int | None = Field(None, description="是否已接受修订。")
    contract_content_path: str | None = Field(None, description="解析后合同正文存储路径。")
    contract_type_id: int | None = Field(None, description="合同类型ID。")
    review_position: int | None = Field(None, description="审查立场编码。")
    file_url: str | None = Field(None, description="按旧上传响应规则计算出的文件访问地址。")


class ReviewTaskSnapshot(AgentContractModel):
    """审阅任务快照，合并旧版任务表和创建请求中的字段。"""

    task_id: int | None = Field(None, description="审阅任务ID。")
    session_id: int | None = Field(None, description="审阅会话ID。")
    file_id: int | None = Field(None, description="审阅关联的合同文件ID。")
    user_id: int | None = Field(None, description="发起审阅的用户ID。")
    type: str | None = Field(None, description="任务类型。")
    stance: str | None = Field(None, description="审查立场。")
    intensity: str | None = Field(None, description="请求中的审查尺度。")
    effective_intensity: str | None = Field(None, description="旧链路实际传入审阅服务的审查尺度。")
    contract_type: str | None = Field(None, description="合同类型。")
    description: str | None = Field(None, description="审查需求描述。")
    status: str | None = Field(None, description="任务状态。")
    max_concurrent: int | None = Field(None, description="请求中的最大并发数。")
    created_at: datetime | None = Field(None, description="任务创建时间。")
    completed_at: datetime | None = Field(None, description="任务完成时间。")


class DocumentContentRef(AgentContractModel):
    """合同正文引用，用于表达正文、正文路径和原文件路径的可用来源。"""

    file_path: str | None = Field(None, description="合同原文件路径。")
    file_type: str | None = Field(None, description="合同文件类型。")
    contract_content_path: str | None = Field(None, description="解析后正文路径。")
    contract_content: str | None = Field(None, description="过渡期可直接传递的合同正文。")
    filename: str | None = Field(None, description="上传文件名。")
    title: str | None = Field(None, description="合同标题。")
    content_source: Literal["contract_content", "contract_content_path", "file_path"] | None = Field(
        None,
        description="当前正文来源。",
    )


class AgentError(AgentContractModel):
    """Agent 错误结构，用于内部降级和 backend 错误映射。"""

    code: str = Field(..., description="错误码。")
    message: str = Field(..., description="可展示错误信息，不包含敏感内容。")
    stage: str = Field(..., description="错误发生阶段。")
    recoverable: bool = Field(False, description="是否可以降级继续。")
    details: dict[str, Any] = Field(default_factory=dict, description="非敏感诊断信息。")


def _main_test_common() -> None:
    """执行通用契约结构的本文件自检。"""

    session = SessionSnapshot(session_id=1, file_id=2, user_id=None, session_type="chat")
    contract = ContractFileSnapshot(file_id=2, title="合同.docx", amount=100.0)
    task = ReviewTaskSnapshot(task_id=3, intensity="严格", effective_intensity="标准")
    ref = DocumentContentRef(file_path="/tmp/contract.docx", content_source="file_path")
    error = AgentError(code="E_TEST", message="测试错误", stage="review")
    assert session.user_id is None
    assert contract.amount == 100.0
    assert task.effective_intensity == "标准"
    assert ref.content_source == "file_path"
    assert error.recoverable is False


if __name__ == "__main__":
    _main_test_common()
