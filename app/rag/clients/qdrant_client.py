"""
Qdrant 客户端封装，用于 RAG 索引与检索。
"""
from __future__ import annotations

from typing import Any, Optional

from app.rag.config import RagQdrantConfig


class QdrantDependencyError(RuntimeError):
    """未安装 qdrant-client 时抛出。"""


class RagQdrantClient:
    """
    Qdrant 客户端轻封装。

    实际第三方依赖采用延迟导入，保证在 `qdrant-client`
    尚未安装前，这个模块仍然可以被正常导入。
    """

    def __init__(self, config: RagQdrantConfig):
        self.config = config
        self._client: Optional[Any] = None

    def _load_client_class(self):
        try:
            from qdrant_client import QdrantClient  # type: ignore
        except ImportError as exc:
            raise QdrantDependencyError(
                "qdrant-client 尚未安装，启用 RAG 检索前需要补充该依赖。"
            ) from exc
        return QdrantClient

    def get_client(self):
        if self._client is None:
            client_cls = self._load_client_class()
            self._client = client_cls(
                host=self.config.host,
                port=self.config.port,
                grpc_port=self.config.grpc_port,
                api_key=self.config.api_key,
                prefer_grpc=self.config.prefer_grpc,
                timeout=self.config.timeout,
            )
        return self._client

    def create_collection(self, name: str, **kwargs):
        """
        collection 创建占位封装。

        调用方需要显式传入向量和 sparse vector 配置。
        """
        client = self.get_client()
        return client.create_collection(collection_name=name, **kwargs)

    def upsert(self, collection_name: str, points: list[Any], **kwargs):
        client = self.get_client()
        return client.upsert(collection_name=collection_name, points=points, **kwargs)

    def search_dense(self, collection_name: str, query_vector: Any, limit: int, **kwargs):
        """
        dense 检索骨架。

        正式实现时需要与实际命名向量字段保持一致。
        """
        client = self.get_client()
        return client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=limit,
            **kwargs,
        )

    def search_sparse(self, collection_name: str, sparse_query: Any, limit: int, **kwargs):
        """
        sparse 检索骨架。

        正式实现时需要传入 Qdrant 所需的 sparse query 结构。
        """
        client = self.get_client()
        return client.query_points(
            collection_name=collection_name,
            query=sparse_query,
            limit=limit,
            **kwargs,
        )

    def search_hybrid(self, collection_name: str, prefetch: list[Any], query: Any, limit: int, **kwargs):
        """
        基于 Qdrant Query API 的 hybrid 检索骨架。
        """
        client = self.get_client()
        return client.query_points(
            collection_name=collection_name,
            prefetch=prefetch,
            query=query,
            limit=limit,
            **kwargs,
        )

    def close(self):
        if self._client is not None and hasattr(self._client, "close"):
            self._client.close()
        self._client = None
