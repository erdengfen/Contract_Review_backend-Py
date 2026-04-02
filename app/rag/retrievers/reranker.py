"""
RAG 重排模块。
"""
from __future__ import annotations

from typing import Any

from app.rag.config import RagConfig
from app.rag.schemas import RetrievalHit


class RagReranker:
    """
    RAG 候选集重排器。

    当前实现保持轻量：
    - 若未启用 rerank，直接返回原结果
    - 若提供自定义 client，则调用 client 的 `rerank` 方法
    - 若没有 client，回退为按已有分数排序
    """

    def __init__(self, config: RagConfig, client: Any = None):
        self.config = config
        self.client = client

    def rerank(self, query: str, hits: list[RetrievalHit], top_n: int | None = None) -> list[RetrievalHit]:
        if not hits:
            return []

        limit = top_n or self.config.rerank.top_n

        if not self.config.rerank.enabled:
            return sorted(hits, key=lambda hit: hit.score, reverse=True)[:limit]

        if self.client is not None and hasattr(self.client, "rerank"):
            reranked_hits = self.client.rerank(query=query, hits=hits, top_n=limit)
            return list(reranked_hits)[:limit]

        return sorted(hits, key=lambda hit: hit.score, reverse=True)[:limit]


class _FakeRerankClient:
    def rerank(self, query: str, hits: list[RetrievalHit], top_n: int) -> list[RetrievalHit]:
        return sorted(hits, key=lambda hit: (len(hit.title), hit.score), reverse=True)[:top_n]


def _main_test_reranker():
    config = RagConfig()
    reranker = RagReranker(config=config, client=_FakeRerankClient())
    hits = [
        RetrievalHit(
            source_collection="external_legal_kb",
            record_id="law-1",
            title="民法典",
            content="当事人应全面履行义务。",
            score=0.8,
        ),
        RetrievalHit(
            source_collection="external_legal_kb",
            record_id="law-2",
            title="中华人民共和国民法典合同编",
            content="合同应遵循诚实信用原则。",
            score=0.7,
        ),
    ]
    reranked = reranker.rerank(query="合同履行", hits=hits, top_n=1)
    assert len(reranked) == 1
    assert reranked[0].record_id == "law-2"
    print("RagReranker self test passed")


if __name__ == "__main__":
    _main_test_reranker()
