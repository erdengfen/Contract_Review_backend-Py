"""
RAG 主编排服务。
"""
from __future__ import annotations

from app.rag.config import RagConfig
from app.rag.retrievers.hybrid_fusion import reciprocal_rank_fusion, take_top_k
from app.rag.retrievers.multi_query import MultiQueryBuilder
from app.rag.schemas import RetrievalHit, RetrievalRequest, RetrievalResponse
from app.rag.services.context_builder import RagContextBuilder


class RagService:
    """
    编排多路 query、双 collection 检索、融合与重排。
    """

    def __init__(
        self,
        *,
        config: RagConfig,
        multi_query_builder: MultiQueryBuilder,
        external_retriever,
        internal_retriever,
        reranker,
        context_builder: RagContextBuilder,
    ):
        self.config = config
        self.multi_query_builder = multi_query_builder
        self.external_retriever = external_retriever
        self.internal_retriever = internal_retriever
        self.reranker = reranker
        self.context_builder = context_builder

    def retrieve_for_review(self, request: RetrievalRequest) -> RetrievalResponse:
        if not self.config.enabled or not self.config.retrieval.enabled:
            return RetrievalResponse()

        query_bundle = self.multi_query_builder.build_queries(request)

        external_ranked_lists = [
            self.external_retriever.retrieve_by_query(query_bundle.raw_chunk_query, request),
            self.external_retriever.retrieve_by_query(query_bundle.legal_issue_query, request),
        ]
        internal_ranked_lists = [
            self.internal_retriever.retrieve_by_query(query_bundle.raw_chunk_query, request),
            self.internal_retriever.retrieve_by_query(query_bundle.risk_tag_query, request),
        ]

        external_fused = reciprocal_rank_fusion(
            external_ranked_lists,
            weights=[
                self.config.retrieval.route_raw_chunk_weight,
                self.config.retrieval.route_legal_issue_weight,
            ],
        )
        internal_fused = reciprocal_rank_fusion(
            internal_ranked_lists,
            weights=[
                self.config.retrieval.route_raw_chunk_weight,
                self.config.retrieval.route_risk_tag_weight,
            ],
        )

        rerank_query = query_bundle.legal_issue_query or query_bundle.raw_chunk_query
        external_top = self.reranker.rerank(
            query=rerank_query,
            hits=take_top_k(external_fused, self.config.retrieval.fused_top_k),
            top_n=self.config.retrieval.final_external_top_k,
        )
        internal_top = self.reranker.rerank(
            query=rerank_query,
            hits=take_top_k(internal_fused, self.config.retrieval.fused_top_k),
            top_n=self.config.retrieval.final_internal_top_k,
        )

        fused_hits: list[RetrievalHit] = reciprocal_rank_fusion(
            [external_top, internal_top],
            weights=[
                self.config.retrieval.external_weight,
                self.config.retrieval.internal_weight,
            ],
        )
        return self.context_builder.build_response(external_top, internal_top, fused_hits)


class _FakeRetriever:
    def __init__(self, collection: str):
        self.collection = collection

    def retrieve_by_query(self, query_text: str, request: RetrievalRequest) -> list[RetrievalHit]:
        if self.collection == "external_legal_kb":
            return [
                RetrievalHit(
                    source_collection="external_legal_kb",
                    record_id="law-1",
                    title="民法典",
                    content=f"法律命中：{query_text}",
                    score=0.9,
                    article_no="第五百零九条",
                    source_type="law",
                )
            ]
        return [
            RetrievalHit(
                source_collection="internal_review_rules",
                record_id="rule-1",
                title="付款条款审阅规则",
                content=f"内部规则命中：{query_text}",
                score=0.88,
                rule_type="review_rule",
            )
        ]


def _main_test_rag_service():
    from app.rag.retrievers.multi_query import MultiQueryBuilder
    from app.rag.retrievers.reranker import RagReranker

    config = RagConfig()
    service = RagService(
        config=config,
        multi_query_builder=MultiQueryBuilder(),
        external_retriever=_FakeRetriever("external_legal_kb"),
        internal_retriever=_FakeRetriever("internal_review_rules"),
        reranker=RagReranker(config=config, client=None),
        context_builder=RagContextBuilder(config=config),
    )
    response = service.retrieve_for_review(
        RetrievalRequest(
            chunk_text="甲方逾期付款应承担违约责任。",
            contract_type="服务合同",
            stance="甲方",
        )
    )
    assert response.external_hits
    assert response.internal_hits
    assert "## 外部法律依据" in response.prompt_context
    assert "## 内部审阅规则" in response.prompt_context
    print("RagService self test passed")


if __name__ == "__main__":
    _main_test_rag_service()
