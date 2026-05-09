"""Agent RAG 命中契约。

本文件定义当前基础重构阶段可承接的检索命中结构。
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from src.agent.contracts.common import AgentContractModel


class KnowledgeHit(AgentContractModel):
    """知识命中结构，承接旧版 RetrievalHit 已有字段。"""

    hit_id: str | None = Field(None, description="知识命中唯一标识。")
    source_collection: Literal["external_legal_kb", "internal_review_rules"] = Field(
        ...,
        description="命中来源集合。",
    )
    record_id: str = Field(..., description="来源记录ID。")
    title: str = Field(..., description="命中结果标题。")
    content: str = Field(..., description="命中结果正文。")
    score: float = Field(..., description="融合后的最终分数。")
    article_no: str | None = Field(None, description="法律条号。")
    rule_type: str | None = Field(None, description="内部规则类型。")
    source_type: str | None = Field(None, description="法律来源类型。")
    payload: dict[str, Any] = Field(default_factory=dict, description="关联 payload。")

    @model_validator(mode="after")
    def fill_hit_id(self) -> "KnowledgeHit":
        """在未传 hit_id 时按来源集合和记录 ID 生成稳定标识。"""

        if self.hit_id is None:
            self.hit_id = f"{self.source_collection}:{self.record_id}"
        return self


def _main_test_rag() -> None:
    """执行 RAG 契约结构的本文件自检。"""

    hit = KnowledgeHit(
        source_collection="external_legal_kb",
        record_id="law-1",
        title="民法典",
        content="测试条文",
        score=0.9,
    )
    assert hit.hit_id == "external_legal_kb:law-1"


if __name__ == "__main__":
    _main_test_rag()
