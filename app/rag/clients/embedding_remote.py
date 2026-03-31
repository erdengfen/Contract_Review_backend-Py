"""
远程 embedding 客户端。
"""
from __future__ import annotations

from typing import Any

from app.rag.config import RagEmbeddingConfig


class RemoteEmbeddingConfigError(RuntimeError):
    """远程 embedding 配置不完整时抛出。"""


class RemoteEmbeddingClient:
    """
    面向 OpenAI 兼容 embedding 服务的远程客户端骨架。

    使用延迟导入，避免在功能尚未正式接线前强依赖远程 SDK。
    """

    def __init__(self, config: RagEmbeddingConfig):
        self.config = config
        self._client: Any = None

    def _validate(self):
        if not self.config.remote_base_url:
            raise RemoteEmbeddingConfigError("远程 embedding 模式下必须配置 remote_base_url。")
        if not self.config.remote_api_key:
            raise RemoteEmbeddingConfigError("远程 embedding 模式下必须配置 remote_api_key。")
        if not self.config.remote_model:
            raise RemoteEmbeddingConfigError("远程 embedding 模式下必须配置 remote_model。")

    def _load_client(self):
        self._validate()
        try:
            from openai import OpenAI  # type: ignore
        except ImportError as exc:
            raise RemoteEmbeddingConfigError(
                "远程 embedding 客户端缺少 openai SDK 依赖。"
            ) from exc
        return OpenAI(
            api_key=self.config.remote_api_key,
            base_url=self.config.remote_base_url,
            timeout=self.config.remote_timeout,
        )

    def get_client(self):
        if self._client is None:
            self._client = self._load_client()
        return self._client

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """调用远程 embedding 接口生成多条向量。"""
        if not texts:
            return []
        client = self.get_client()
        response = client.embeddings.create(
            model=self.config.remote_model,
            input=texts,
        )
        return [item.embedding for item in response.data]

    def embed_query(self, text: str) -> list[float]:
        """调用远程 embedding 接口生成单条 query 向量。"""
        client = self.get_client()
        response = client.embeddings.create(
            model=self.config.remote_model,
            input=[text],
        )
        return response.data[0].embedding


class _FakeEmbeddingItem:
    def __init__(self, embedding: list[float]):
        self.embedding = embedding


class _FakeEmbeddingResponse:
    def __init__(self, embeddings: list[list[float]]):
        self.data = [_FakeEmbeddingItem(embedding) for embedding in embeddings]


class _FakeEmbeddingsAPI:
    def create(self, *, model: str, input):
        if isinstance(input, str):
            input = [input]
        vectors = []
        for idx, _ in enumerate(input, start=1):
            vectors.append([float(idx), float(idx + 1), float(idx + 2)])
        return _FakeEmbeddingResponse(vectors)


class _FakeRemoteClient:
    def __init__(self):
        self.embeddings = _FakeEmbeddingsAPI()


class _TestableRemoteEmbeddingClient(RemoteEmbeddingClient):
    def _load_client(self):
        self._validate()
        return _FakeRemoteClient()


def _main_test_remote_embedding():
    config = RagEmbeddingConfig(
        provider_mode="remote",
        remote_model="text-embedding-3-small",
        remote_base_url="https://example.com/v1",
        remote_api_key="test-key",
    )
    client = _TestableRemoteEmbeddingClient(config)
    docs = client.embed_documents(["法规一", "法规二"])
    query = client.embed_query("付款条款")
    assert len(docs) == 2
    assert len(docs[0]) == 3
    assert len(query) == 3
    print("RemoteEmbeddingClient self test passed")


if __name__ == "__main__":
    _main_test_remote_embedding()
