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
        if not texts:
            return []
        client = self.get_client()
        response = client.embeddings.create(
            model=self.config.remote_model,
            input=texts,
        )
        return [item.embedding for item in response.data]

    def embed_query(self, text: str) -> list[float]:
        client = self.get_client()
        response = client.embeddings.create(
            model=self.config.remote_model,
            input=[text],
        )
        return response.data[0].embedding
