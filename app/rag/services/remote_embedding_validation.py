"""
远程 embedding provider 真实联调入口。
"""
from __future__ import annotations

import argparse
import json
from typing import Any

from app.config.config import settings
from app.rag.clients.embedding_remote import RemoteEmbeddingClient, _TestableRemoteEmbeddingClient
from app.rag.clients.qdrant_client import RagQdrantClient
from app.rag.config import RagConfig
from app.rag.retrievers.external_legal_retriever import ExternalLegalRetriever
from app.rag.retrievers.internal_rules_retriever import InternalRulesRetriever
from app.rag.retrievers.multi_query import MultiQueryBuilder
from app.rag.retrievers.reranker import RagReranker
from app.rag.schemas import RetrievalRequest
from app.rag.services.context_builder import RagContextBuilder
from app.rag.services.rag_service import RagService
from app.rag.services.retrieval_validation import DEFAULT_CHUNK_TEXT, response_to_summary


def build_remote_validation_config(
    *,
    remote_model: str | None = None,
    remote_base_url: str | None = None,
    remote_api_key: str | None = None,
) -> RagConfig:
    config = settings.rag_config.model_copy(deep=True)
    config.embedding.provider_mode = "remote"
    if remote_model:
        config.embedding.remote_model = remote_model
    if remote_base_url:
        config.embedding.remote_base_url = remote_base_url
    if remote_api_key:
        config.embedding.remote_api_key = remote_api_key
    return config


def build_remote_validation_service(config: RagConfig) -> RagService:
    qdrant_client = RagQdrantClient(config.qdrant)
    embedding_client = RemoteEmbeddingClient(config.embedding)
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
        reranker=RagReranker(config=config),
        context_builder=RagContextBuilder(config=config),
    )


def run_remote_embedding_validation(
    *,
    chunk_text: str,
    contract_type: str,
    stance: str,
    remote_model: str | None,
    remote_base_url: str | None,
    remote_api_key: str | None,
    with_retrieval: bool,
) -> dict[str, Any]:
    config = build_remote_validation_config(
        remote_model=remote_model,
        remote_base_url=remote_base_url,
        remote_api_key=remote_api_key,
    )
    embedding_client = RemoteEmbeddingClient(config.embedding)
    document_vectors = embedding_client.embed_documents([chunk_text, contract_type])
    query_vector = embedding_client.embed_query(chunk_text)
    payload: dict[str, Any] = {
        "embedding": {
            "provider_mode": config.embedding.provider_mode,
            "remote_provider": config.embedding.remote_provider,
            "remote_model": config.embedding.remote_model,
            "remote_base_url": config.embedding.remote_base_url,
            "document_vector_count": len(document_vectors),
            "document_vector_dim": len(document_vectors[0]) if document_vectors else 0,
            "query_vector_dim": len(query_vector),
        }
    }
    if with_retrieval:
        service = build_remote_validation_service(config)
        response = service.retrieve_for_review(
            RetrievalRequest(
                chunk_text=chunk_text,
                contract_type=contract_type,
                stance=stance,
            )
        )
        payload["retrieval"] = response_to_summary(response)
    return payload


def _main_test_remote_embedding_validation():
    config = build_remote_validation_config(
        remote_model="text-embedding-3-small",
        remote_base_url="https://example.com/v1",
        remote_api_key="test-key",
    )
    client = _TestableRemoteEmbeddingClient(config.embedding)
    docs = client.embed_documents(["样本一", "样本二"])
    query = client.embed_query("付款条款")
    assert len(docs) == 2
    assert len(docs[0]) == 3
    assert len(query) == 3
    print("remote embedding validation self test passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="远程 embedding provider 真实联调入口")
    parser.add_argument("--chunk-text", default=DEFAULT_CHUNK_TEXT, help="待检索的合同片段")
    parser.add_argument("--contract-type", default="服务合同", help="合同类型")
    parser.add_argument("--stance", default="甲方", help="审阅立场")
    parser.add_argument("--remote-model", help="远程 embedding 模型名称")
    parser.add_argument("--remote-base-url", help="远程 embedding 服务地址")
    parser.add_argument("--remote-api-key", help="远程 embedding API Key")
    parser.add_argument("--with-retrieval", action="store_true", help="同时验证真实 Qdrant 检索链路")
    parser.add_argument("--self-test", action="store_true", help="执行文件内自测")
    args = parser.parse_args()

    if args.self_test:
        _main_test_remote_embedding_validation()
    else:
        result = run_remote_embedding_validation(
            chunk_text=args.chunk_text,
            contract_type=args.contract_type,
            stance=args.stance,
            remote_model=args.remote_model,
            remote_base_url=args.remote_base_url,
            remote_api_key=args.remote_api_key,
            with_retrieval=args.with_retrieval,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
