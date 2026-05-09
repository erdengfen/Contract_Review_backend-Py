"""Agent 契约包导出。

本文件集中导出 Step 3 契约结构，便于后续 backend adapter 和 agent 能力模块引用。
"""
from src.agent.contracts.chat import (
    ChatDonePayload,
    ChatErrorPayload,
    ChatMessage,
    ChatRequest,
    ChatResponseChunk,
)
from src.agent.contracts.common import (
    AgentContractModel,
    AgentError,
    ContractFileSnapshot,
    DocumentContentRef,
    ReviewTaskSnapshot,
    SessionSnapshot,
)
from src.agent.contracts.document import (
    ContractInfoExtraction,
    DocumentBlock,
    DocumentIntakeRequest,
    DocumentIntakeResponse,
    ParsedDocument,
    SourceLocation,
)
from src.agent.contracts.rag import KnowledgeHit
from src.agent.contracts.review import (
    ReviewExecutionOptions,
    ReviewRequest,
    ReviewResponse,
    ReviewRiskItem,
    ReviewStreamEvent,
    ReviewSummary,
)

__all__ = [
    "AgentContractModel",
    "AgentError",
    "ChatDonePayload",
    "ChatErrorPayload",
    "ChatMessage",
    "ChatRequest",
    "ChatResponseChunk",
    "ContractFileSnapshot",
    "ContractInfoExtraction",
    "DocumentBlock",
    "DocumentContentRef",
    "DocumentIntakeRequest",
    "DocumentIntakeResponse",
    "KnowledgeHit",
    "ParsedDocument",
    "ReviewExecutionOptions",
    "ReviewRequest",
    "ReviewResponse",
    "ReviewRiskItem",
    "ReviewStreamEvent",
    "ReviewSummary",
    "ReviewTaskSnapshot",
    "SessionSnapshot",
    "SourceLocation",
]


def _main_test_exports() -> None:
    """执行契约包导出的本文件自检。"""

    exported_names = set(__all__)
    assert "ReviewRequest" in exported_names
    assert "ChatRequest" in exported_names
    assert "DocumentIntakeRequest" in exported_names
    assert "KnowledgeHit" in exported_names


if __name__ == "__main__":
    _main_test_exports()
