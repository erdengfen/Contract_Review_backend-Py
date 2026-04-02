"""
RAG 组件实例化工厂。
"""
from __future__ import annotations

from typing import Any

from app.rag.clients.embedding_local import LocalEmbeddingClient
from app.rag.clients.embedding_remote import RemoteEmbeddingClient
from app.rag.clients.qdrant_client import RagQdrantClient
from app.rag.config import RagConfig
from app.rag.retrievers.external_legal_retriever import ExternalLegalRetriever
from app.rag.retrievers.internal_rules_retriever import InternalRulesRetriever
from app.rag.retrievers.multi_query import MultiQueryBuilder
from app.rag.retrievers.reranker import RagReranker
from app.rag.services.context_builder import RagContextBuilder
from app.rag.services.rag_service import RagService


def build_embedding_client(config: RagConfig) -> Any:
    """
    按配置构造 embedding 客户端。
    """
    provider_mode = config.embedding.provider_mode
    if provider_mode == "local":
        return LocalEmbeddingClient(config=config)
    if provider_mode == "remote":
        return RemoteEmbeddingClient(config=config)
    raise ValueError(f"不支持的 embedding provider_mode: {provider_mode}")


def build_rag_service(config: RagConfig) -> RagService:
    """
    构造 RAG 主服务。
    """
    qdrant_client = RagQdrantClient(config=config)
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


def _main_test_rag_factory():
    config = RagConfig()
    service = build_rag_service(config)
    assert service.config.qdrant.external_collection == "external_legal_kb"
    assert service.config.qdrant.internal_collection == "internal_review_rules"
    assert service.external_retriever is not None
    assert service.internal_retriever is not None
    print("RAG factory self test passed")


if __name__ == "__main__":
    _main_test_rag_factory()
