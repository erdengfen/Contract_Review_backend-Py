"""Agent 合同审阅契约。

本文件定义 backend 调用 agent 审阅能力时使用的请求、结果和流式事件结构。
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from src.agent.contracts.common import (
    AgentContractModel,
    AgentError,
    ContractFileSnapshot,
    DocumentContentRef,
    ReviewTaskSnapshot,
    SessionSnapshot,
)
from src.agent.contracts.document import DocumentBlock


class ReviewExecutionOptions(AgentContractModel):
    """审阅执行参数，记录旧链路并发、切块和强制审查尺度行为。"""

    max_concurrent: int | None = Field(None, description="请求中的最大并发数。")
    chunk_max_length: int = Field(4000, description="旧版长度切块上限。")
    ordered_emit: bool = Field(True, description="是否按分块顺序输出。")
    continue_on_chunk_error: bool = Field(True, description="单分块失败时是否继续。")
    requested_intensity: str | None = Field(None, description="请求中的审查尺度。")
    effective_intensity: str | None = Field("标准", description="旧链路实际使用的审查尺度。")
    stance: str | None = Field(None, description="审查立场。")
    contract_type: str | None = Field(None, description="合同类型。")
    description: str | None = Field(None, description="审查需求描述。")


class ReviewRequest(AgentContractModel):
    """审阅请求，承接旧版任务、会话、合同和正文引用的完整上下文。"""

    task: ReviewTaskSnapshot = Field(..., description="审阅任务快照。")
    session: SessionSnapshot = Field(..., description="会话快照。")
    contract: ContractFileSnapshot = Field(..., description="合同文件快照。")
    document: DocumentContentRef = Field(..., description="合同正文引用。")
    options: ReviewExecutionOptions = Field(default_factory=ReviewExecutionOptions, description="审阅执行参数。")
    prebuilt_blocks: list[DocumentBlock] = Field(default_factory=list, description="过渡期预构建分块。")


class ReviewRiskItem(AgentContractModel):
    """审阅风险点，覆盖当前落库字段和旧解析器可解析出的完整字段。"""

    index: int | None = Field(None, description="风险点全局序号。")
    position: str | None = Field(None, description="旧解析器中的修改点位置。")
    original_content: str = Field(..., description="原始条款内容。")
    risk_analysis: str = Field(..., description="风险分析。")
    risk_level: str = Field(..., description="风险等级。")
    suggested_content: str = Field(..., description="建议修改内容。")
    reason: str | None = Field(None, description="修改理由。")
    risk_type: str | None = Field(None, description="风险类型。")
    priority: str | None = Field(None, description="兜底结构中的优先级。")
    action: str | None = Field(None, description="兜底结构中的处理动作。")
    source_block_ids: list[str] = Field(default_factory=list, description="关联文档块ID。")
    knowledge_hit_ids: list[str] = Field(default_factory=list, description="关联知识命中ID。")
    parser_status: Literal["parsed", "fallback", "failed"] = Field("parsed", description="解析状态。")


class ReviewSummary(AgentContractModel):
    """审阅摘要，供 agent 内部返回，最终仍由 backend 映射旧 SSE。"""

    total_issues: int = Field(0, description="风险点数量。")
    overall_risk: str | None = Field(None, description="整体风险等级。")
    summary: str | None = Field(None, description="审阅摘要。")
    suggestion: str | None = Field(None, description="处理建议。")


class ReviewResponse(AgentContractModel):
    """审阅完整响应，供 backend adapter 映射落库和 SSE。"""

    task_id: int | None = Field(None, description="审阅任务ID。")
    session_id: int | None = Field(None, description="会话ID。")
    file_id: int | None = Field(None, description="合同文件ID。")
    items: list[ReviewRiskItem] = Field(default_factory=list, description="风险点列表。")
    summary: ReviewSummary | None = Field(None, description="审阅摘要。")
    errors: list[AgentError] = Field(default_factory=list, description="错误和降级信息。")
    fallback_used: bool = Field(False, description="是否使用降级审阅。")


class ReviewStreamEvent(AgentContractModel):
    """审阅流式事件，供 backend 映射为旧 ReviewTaskSSEResponse。"""

    event: Literal["message", "end", "error"] = Field(..., description="事件类型。")
    data: dict[str, Any] = Field(default_factory=dict, description="事件数据。")
    sequence: int | None = Field(None, description="事件顺序。")


def _main_test_review() -> None:
    """执行审阅契约结构的本文件自检。"""

    request = ReviewRequest(
        task=ReviewTaskSnapshot(task_id=1, session_id=2, file_id=3),
        session=SessionSnapshot(session_id=2, file_id=3),
        contract=ContractFileSnapshot(file_id=3, title="合同.docx"),
        document=DocumentContentRef(contract_content_path="/tmp/contract.txt"),
    )
    item = ReviewRiskItem(
        original_content="付款条款",
        risk_analysis="付款条件不明确",
        risk_level="中",
        suggested_content="明确付款条件。",
    )
    response = ReviewResponse(task_id=1, session_id=2, file_id=3, items=[item])
    assert request.options.effective_intensity == "标准"
    assert response.items[0].risk_level == "中"


if __name__ == "__main__":
    _main_test_review()
