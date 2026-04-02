"""
RAG 检索链路验证入口。
"""
from __future__ import annotations

import argparse
import json

from app.config.config import settings
from app.rag.clients.fake_embedding import DeterministicFakeEmbeddingClient
from app.rag.clients.qdrant_client import RagQdrantClient
from app.rag.retrievers.external_legal_retriever import ExternalLegalRetriever
from app.rag.retrievers.internal_rules_retriever import InternalRulesRetriever
from app.rag.retrievers.multi_query import MultiQueryBuilder
from app.rag.retrievers.reranker import RagReranker
from app.rag.schemas import RetrievalHit, RetrievalRequest
from app.rag.services.context_builder import RagContextBuilder
from app.rag.services.rag_service import RagService


DEFAULT_CHUNK_TEXT = "合同格式条款提供方减轻自身责任，且付款条件不明确，违约责任未量化。"


def build_validation_service(use_fake_embedding: bool = True) -> RagService:
    config = settings.rag_config
    qdrant_client = RagQdrantClient(config.qdrant)
    if use_fake_embedding:
        embedding_client = DeterministicFakeEmbeddingClient(dim=config.qdrant.dense_vector_size)
    else:
        from app.rag.factory import build_embedding_client

        embedding_client = build_embedding_client(config)

    return RagService(
        config=config,
        multi_query_builder=MultiQueryBuilder(),
        external_retriever=ExternalLegalRetriever(
            qdrant_client=qdrant_client,
            embedding_client=embedding_client,
            config=config,
        ),
        internal_retriever=InternalRulesRetriever(
            qdrant_client=qdrant_client,
            embedding_client=embedding_client,
            config=config,
        ),
        reranker=RagReranker(config=config, client=None),
        context_builder=RagContextBuilder(config=config),
    )


def response_to_summary(response) -> dict:
    def simplify(hit: RetrievalHit) -> dict:
        return {
            "record_id": hit.record_id,
            "title": hit.title,
            "score": hit.score,
            "article_no": hit.article_no,
            "rule_type": hit.rule_type,
            "source_type": hit.source_type,
        }

    return {
        "external_hits": [simplify(hit) for hit in response.external_hits],
        "internal_hits": [simplify(hit) for hit in response.internal_hits],
        "prompt_context": response.prompt_context,
    }


def _main_test_retrieval_validation():
    request = RetrievalRequest(
        chunk_text=DEFAULT_CHUNK_TEXT,
        contract_type="服务合同",
        stance="甲方",
    )
    builder = MultiQueryBuilder()
    bundle = builder.build_queries(request)
    assert "付款条款" in bundle.risk_tags
    assert "违约责任" in bundle.risk_tags
    print("Retrieval validation self test passed")


def _run_cli(chunk_text: str, contract_type: str, stance: str, use_fake_embedding: bool):
    service = build_validation_service(use_fake_embedding=use_fake_embedding)
    response = service.retrieve_for_review(
        RetrievalRequest(
            chunk_text=chunk_text,
            contract_type=contract_type,
            stance=stance,
        )
    )
    print(json.dumps(response_to_summary(response), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RAG 检索链路验证入口")
    parser.add_argument("--chunk-text", default=DEFAULT_CHUNK_TEXT, help="待检索的合同片段")
    parser.add_argument("--contract-type", default="服务合同", help="合同类型")
    parser.add_argument("--stance", default="甲方", help="审阅立场")
    parser.add_argument(
        "--fake-embedding",
        action="store_true",
        help="使用确定性假 embedding，验证真实 Qdrant 检索链路",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="执行文件内自测",
    )
    args = parser.parse_args()

    if args.self_test:
        _main_test_retrieval_validation()
    else:
        _run_cli(
            chunk_text=args.chunk_text,
            contract_type=args.contract_type,
            stance=args.stance,
            use_fake_embedding=args.fake_embedding,
        )
