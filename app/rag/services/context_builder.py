"""
RAG prompt 上下文构建模块。
"""
from __future__ import annotations

from app.rag.config import RagConfig
from app.rag.schemas import RetrievalHit, RetrievalResponse


class RagContextBuilder:
    """
    将检索结果转为可直接注入 prompt 的文本。
    """

    def __init__(self, config: RagConfig):
        self.config = config

    def _format_external_hit(self, hit: RetrievalHit, index: int) -> str:
        article_no = f" {hit.article_no}" if hit.article_no else ""
        return (
            f"{index}. {hit.title}{article_no}\n"
            f"   来源类型：{hit.source_type or '未知'}\n"
            f"   内容：{hit.content}"
        )

    def _format_internal_hit(self, hit: RetrievalHit, index: int) -> str:
        rule_type = f"（{hit.rule_type}）" if hit.rule_type else ""
        return (
            f"{index}. {hit.title}{rule_type}\n"
            f"   规则ID：{hit.record_id}\n"
            f"   内容：{hit.content}"
        )

    def build_prompt_context(
        self,
        external_hits: list[RetrievalHit],
        internal_hits: list[RetrievalHit],
    ) -> str:
        sections: list[str] = []

        if external_hits:
            lines = ["## 外部法律依据"]
            for idx, hit in enumerate(external_hits, start=1):
                lines.append(self._format_external_hit(hit, idx))
            sections.append("\n".join(lines))

        if internal_hits:
            lines = ["## 内部审阅规则"]
            for idx, hit in enumerate(internal_hits, start=1):
                lines.append(self._format_internal_hit(hit, idx))
            sections.append("\n".join(lines))

        prompt_context = "\n\n".join(sections).strip()
        if len(prompt_context) > self.config.retrieval.max_context_chars:
            prompt_context = prompt_context[: self.config.retrieval.max_context_chars].rstrip()
        return prompt_context

    def build_response(
        self,
        external_hits: list[RetrievalHit],
        internal_hits: list[RetrievalHit],
        fused_hits: list[RetrievalHit],
    ) -> RetrievalResponse:
        prompt_context = self.build_prompt_context(external_hits, internal_hits)
        return RetrievalResponse(
            external_hits=external_hits,
            internal_hits=internal_hits,
            fused_hits=fused_hits,
            prompt_context=prompt_context,
        )


def _main_test_context_builder():
    config = RagConfig()
    builder = RagContextBuilder(config)
    external_hits = [
        RetrievalHit(
            source_collection="external_legal_kb",
            record_id="law-1",
            title="民法典",
            content="当事人应全面履行义务。",
            score=0.9,
            article_no="第五百零九条",
            source_type="law",
        )
    ]
    internal_hits = [
        RetrievalHit(
            source_collection="internal_review_rules",
            record_id="rule-1",
            title="付款条款审阅规则",
            content="付款条款必须明确付款期限。",
            score=0.8,
            rule_type="review_rule",
        )
    ]
    response = builder.build_response(external_hits, internal_hits, external_hits + internal_hits)
    assert "## 外部法律依据" in response.prompt_context
    assert "## 内部审阅规则" in response.prompt_context
    print("RagContextBuilder self test passed")


if __name__ == "__main__":
    _main_test_context_builder()
