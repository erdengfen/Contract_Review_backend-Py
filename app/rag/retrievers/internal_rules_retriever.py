"""
内部规则库检索器。
"""
from __future__ import annotations

import hashlib
import re
from types import SimpleNamespace
from typing import Any

from qdrant_client.http import models

from app.rag.config import RagConfig
from app.rag.retrievers.hybrid_fusion import reciprocal_rank_fusion, take_top_k
from app.rag.schemas import RetrievalHit, RetrievalRequest


class InternalRulesRetriever:
    """
    面向 `internal_review_rules` 的检索器。
    """

    def __init__(self, qdrant_client: Any, embedding_client: Any, config: RagConfig):
        self.qdrant_client = qdrant_client
        self.embedding_client = embedding_client
        self.config = config

    def _tokenize(self, text: str) -> list[str]:
        tokens = re.findall(r"[\u4e00-\u9fff]+|[A-Za-z0-9_]+", text)
        return [token.lower() for token in tokens if token.strip()]

    def _build_sparse_query(self, text: str) -> models.SparseVector:
        token_counts: dict[int, float] = {}
        for token in self._tokenize(text):
            index = int(hashlib.md5(token.encode("utf-8")).hexdigest()[:8], 16) % 50000
            token_counts[index] = token_counts.get(index, 0.0) + 1.0
        indices = sorted(token_counts.keys())
        values = [token_counts[index] for index in indices]
        return models.SparseVector(indices=indices, values=values)

    def _build_filters(self, request: RetrievalRequest):
        field_filters = {
            "organization_scope": request.filters.organization_scope,
            "enabled": True if self.config.filters.internal_rules_enabled_only else None,
        }
        return self.qdrant_client.build_match_filter(field_filters)

    def _extract_points(self, response: Any) -> list[Any]:
        if response is None:
            return []
        if isinstance(response, list):
            return response
        if hasattr(response, "points"):
            return list(response.points)
        if isinstance(response, dict) and "points" in response:
            return list(response["points"])
        return []

    def _point_to_hit(self, point: Any) -> RetrievalHit:
        payload = getattr(point, "payload", {}) or {}
        point_id = getattr(point, "id", payload.get("rule_id", ""))
        score = float(getattr(point, "score", 0.0))
        return RetrievalHit(
            source_collection="internal_review_rules",
            record_id=str(point_id),
            title=payload.get("title", ""),
            content=payload.get("content", ""),
            score=score,
            rule_type=payload.get("rule_type"),
            payload=payload,
        )

    def retrieve_by_query(self, query_text: str, request: RetrievalRequest) -> list[RetrievalHit]:
        limit = self.config.retrieval.per_route_top_k
        query_filter = self._build_filters(request)
        ranked_lists: list[list[RetrievalHit]] = []

        if self.config.retrieval.enable_dense:
            dense_vector = self.embedding_client.embed_query(query_text)
            dense_response = self.qdrant_client.search_dense(
                self.config.qdrant.internal_collection,
                dense_vector,
                limit=limit,
                query_filter=query_filter,
            )
            dense_hits = [self._point_to_hit(point) for point in self._extract_points(dense_response)]
            ranked_lists.append(dense_hits)

        if self.config.retrieval.enable_sparse:
            sparse_query = self._build_sparse_query(query_text)
            sparse_response = self.qdrant_client.search_sparse(
                self.config.qdrant.internal_collection,
                sparse_query,
                limit=limit,
                query_filter=query_filter,
            )
            sparse_hits = [self._point_to_hit(point) for point in self._extract_points(sparse_response)]
            ranked_lists.append(sparse_hits)

        fused = reciprocal_rank_fusion(ranked_lists)
        return take_top_k(fused, self.config.retrieval.final_internal_top_k)


class _FakeEmbeddingClient:
    def embed_query(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]


class _FakeQdrantClient:
    def build_match_filter(self, field_filters: dict[str, Any]):
        return {"must": field_filters}

    def search_dense(self, collection_name: str, query_vector: Any, limit: int, **kwargs):
        return SimpleNamespace(
            points=[
                SimpleNamespace(
                    id="rule-1",
                    score=0.93,
                    payload={
                        "title": "付款条款审阅规则",
                        "content": "付款条款必须明确付款条件、付款期限和逾期责任。",
                        "rule_type": "review_rule",
                    },
                ),
                SimpleNamespace(
                    id="rule-2",
                    score=0.80,
                    payload={
                        "title": "违约责任规则",
                        "content": "违约责任条款应明确违约金或损失赔偿机制。",
                        "rule_type": "risk_rule",
                    },
                ),
            ]
        )

    def search_sparse(self, collection_name: str, sparse_query: Any, limit: int, **kwargs):
        return SimpleNamespace(
            points=[
                SimpleNamespace(
                    id="rule-1",
                    score=0.85,
                    payload={
                        "title": "付款条款审阅规则",
                        "content": "付款条款必须明确付款条件、付款期限和逾期责任。",
                        "rule_type": "review_rule",
                    },
                )
            ]
        )


def _main_test_internal_rules_retriever():
    from app.rag.config import RagConfig

    retriever = InternalRulesRetriever(
        qdrant_client=_FakeQdrantClient(),
        embedding_client=_FakeEmbeddingClient(),
        config=RagConfig(),
    )
    request = RetrievalRequest(
        chunk_text="甲方逾期付款应承担违约责任。",
        contract_type="服务合同",
    )
    hits = retriever.retrieve_by_query("付款条款 违约责任", request)
    assert len(hits) >= 1
    assert hits[0].record_id == "rule-1"
    print("InternalRulesRetriever self test passed")


if __name__ == "__main__":
    _main_test_internal_rules_retriever()
