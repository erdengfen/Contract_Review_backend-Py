"""
Qdrant 客户端封装，用于 RAG 索引与检索。
"""
from __future__ import annotations

import sys
from typing import Any, Optional
from pathlib import Path

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
        self.default_dense_vector_name = "dense"
        self.default_sparse_vector_name = "sparse"

    def _load_client_class(self):
        try:
            from qdrant_client import QdrantClient  # type: ignore
        except ImportError as exc:
            raise QdrantDependencyError(
                "qdrant-client 尚未安装，启用 RAG 检索前需要补充该依赖。"
            ) from exc
        return QdrantClient

    def _load_models(self):
        try:
            from qdrant_client import models  # type: ignore
        except ImportError as exc:
            raise QdrantDependencyError(
                "qdrant-client 尚未安装，无法加载 Qdrant models。"
            ) from exc
        return models

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

    def collection_exists(self, name: str) -> bool:
        client = self.get_client()
        return client.collection_exists(name)

    def create_collection(self, name: str, **kwargs):
        """
        collection 创建占位封装。

        调用方需要显式传入向量和 sparse vector 配置。
        """
        client = self.get_client()
        return client.create_collection(collection_name=name, **kwargs)

    def create_dense_sparse_collection(
        self,
        *,
        name: str,
        dense_size: int,
        distance: str = "Cosine",
        dense_vector_name: Optional[str] = None,
        sparse_vector_name: Optional[str] = None,
        recreate: bool = False,
    ) -> bool:
        """
        创建同时支持 dense + sparse 的 collection。
        """
        client = self.get_client()
        models = self._load_models()
        dense_name = dense_vector_name or self.default_dense_vector_name
        sparse_name = sparse_vector_name or self.default_sparse_vector_name

        if recreate and client.collection_exists(name):
            client.delete_collection(name)

        if client.collection_exists(name):
            return True

        return client.create_collection(
            collection_name=name,
            vectors_config={
                dense_name: models.VectorParams(
                    size=dense_size,
                    distance=getattr(models.Distance, distance.upper()),
                )
            },
            sparse_vectors_config={
                sparse_name: models.SparseVectorParams(
                    modifier=models.Modifier.IDF,
                )
            },
        )

    def build_match_filter(self, field_filters: dict[str, Any]):
        """
        根据简单键值对构造 Qdrant Filter。
        """
        models = self._load_models()
        conditions = []
        for key, value in field_filters.items():
            if value is None:
                continue
            conditions.append(
                models.FieldCondition(
                    key=key,
                    match=models.MatchValue(value=value),
                )
            )
        if not conditions:
            return None
        return models.Filter(must=conditions)

    def build_point(
        self,
        *,
        point_id: str | int,
        dense_vector: list[float],
        payload: dict[str, Any],
        sparse_indices: Optional[list[int]] = None,
        sparse_values: Optional[list[float]] = None,
        dense_vector_name: Optional[str] = None,
        sparse_vector_name: Optional[str] = None,
    ):
        """
        构造同时包含 dense 和 sparse 向量的 PointStruct。
        """
        models = self._load_models()
        vectors: dict[str, Any] = {
            dense_vector_name or self.default_dense_vector_name: dense_vector,
        }
        if sparse_indices and sparse_values:
            vectors[sparse_vector_name or self.default_sparse_vector_name] = (
                models.SparseVector(
                    indices=sparse_indices,
                    values=sparse_values,
                )
            )
        return models.PointStruct(
            id=point_id,
            vector=vectors,
            payload=payload,
        )

    def upsert(self, collection_name: str, points: list[Any], **kwargs):
        client = self.get_client()
        return client.upsert(collection_name=collection_name, points=points, **kwargs)

    def search_dense(
        self,
        collection_name: str,
        query_vector: Any,
        limit: int,
        *,
        vector_name: Optional[str] = None,
        query_filter: Any = None,
        **kwargs,
    ):
        """
        dense 检索骨架。

        正式实现时需要与实际命名向量字段保持一致。
        """
        client = self.get_client()
        models = self._load_models()
        return client.query_points(
            collection_name=collection_name,
            query=models.NamedVector(
                name=vector_name or self.default_dense_vector_name,
                vector=query_vector,
            ),
            query_filter=query_filter,
            limit=limit,
            **kwargs,
        )

    def search_sparse(
        self,
        collection_name: str,
        sparse_query: Any,
        limit: int,
        *,
        vector_name: Optional[str] = None,
        query_filter: Any = None,
        **kwargs,
    ):
        """
        sparse 检索骨架。

        正式实现时需要传入 Qdrant 所需的 sparse query 结构。
        """
        client = self.get_client()
        models = self._load_models()
        query = (
            sparse_query
            if isinstance(sparse_query, models.NamedSparseVector)
            else models.NamedSparseVector(
                name=vector_name or self.default_sparse_vector_name,
                vector=sparse_query,
            )
        )
        return client.query_points(
            collection_name=collection_name,
            query=query,
            query_filter=query_filter,
            limit=limit,
            **kwargs,
        )

    def search_hybrid(
        self,
        collection_name: str,
        prefetch: list[Any],
        query: Any = None,
        limit: int = 10,
        *,
        query_filter: Any = None,
        **kwargs,
    ):
        """
        基于 Qdrant Query API 的 hybrid 检索骨架。
        """
        client = self.get_client()
        models = self._load_models()
        return client.query_points(
            collection_name=collection_name,
            prefetch=prefetch,
            query=query or models.FusionQuery(fusion=models.Fusion.RRF),
            query_filter=query_filter,
            limit=limit,
            **kwargs,
        )

    def close(self):
        if self._client is not None and hasattr(self._client, "close"):
            self._client.close()
        self._client = None


class _FakeQdrantClient:
    def __init__(self):
        self.collections = set()
        self.closed = False

    def collection_exists(self, name: str) -> bool:
        return name in self.collections

    def delete_collection(self, name: str):
        self.collections.discard(name)

    def create_collection(self, collection_name: str, **kwargs):
        self.collections.add(collection_name)
        return True

    def upsert(self, collection_name: str, points: list[Any], **kwargs):
        return {"collection_name": collection_name, "points_count": len(points)}

    def query_points(self, collection_name: str, **kwargs):
        return {"collection_name": collection_name, "kwargs": kwargs}

    def close(self):
        self.closed = True


class _TestableRagQdrantClient(RagQdrantClient):
    def _load_models(self):
        current_dir = str(Path(__file__).resolve().parent)
        removed = False
        if current_dir in sys.path:
            sys.path.remove(current_dir)
            removed = True
        from qdrant_client.http import models  # type: ignore

        if removed:
            sys.path.insert(0, current_dir)
        return models

    def get_client(self):
        if self._client is None:
            self._client = _FakeQdrantClient()
        return self._client


def _main_test_qdrant_client():
    config = RagQdrantConfig()
    client = _TestableRagQdrantClient(config)
    assert client.collection_exists("demo") is False
    created = client.create_dense_sparse_collection(name="demo", dense_size=3)
    assert created is True
    assert client.collection_exists("demo") is True

    filter_obj = client.build_match_filter(
        {"region": "CN", "effective_status": "effective", "skip": None}
    )
    assert filter_obj is not None

    point = client.build_point(
        point_id="doc-1",
        dense_vector=[0.1, 0.2, 0.3],
        payload={"title": "测试法规"},
        sparse_indices=[1, 2],
        sparse_values=[0.5, 0.6],
    )
    result = client.upsert("demo", [point])
    assert result["points_count"] == 1

    dense_result = client.search_dense("demo", [0.1, 0.2, 0.3], limit=5)
    sparse_result = client.search_sparse(
        "demo",
        client._load_models().SparseVector(indices=[1], values=[1.0]),
        limit=5,
    )
    hybrid_result = client.search_hybrid("demo", prefetch=[], limit=5)
    assert dense_result["collection_name"] == "demo"
    assert sparse_result["collection_name"] == "demo"
    assert hybrid_result["collection_name"] == "demo"

    client.close()
    assert client._client is None
    print("RagQdrantClient self test passed")


if __name__ == "__main__":
    _main_test_qdrant_client()
