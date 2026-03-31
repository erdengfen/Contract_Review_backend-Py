"""
本地轻量 embedding 客户端。
"""
from __future__ import annotations

from typing import Any

from app.rag.config import RagEmbeddingConfig


class LocalEmbeddingDependencyError(RuntimeError):
    """本地 embedding 依赖不可用时抛出。"""


class LocalEmbeddingClient:
    """
    本地轻量 embedding 客户端骨架。

    最终实现可以接 sentence-transformers、FlagEmbedding
    或其他轻量本地模型后端。第三方依赖保持延迟导入，避免在依赖
    未安装前破坏整体可导入性。
    """

    def __init__(self, config: RagEmbeddingConfig):
        self.config = config
        self._model: Any = None

    def _load_backend(self):
        """
        延迟加载本地 embedding 后端。

        这里需要在后续接入实际选定的轻量模型实现。
        """
        raise LocalEmbeddingDependencyError(
            "本地 embedding 后端尚未实现，请先选定并安装轻量模型依赖。"
        )

    def get_model(self):
        if self._model is None:
            self._model = self._load_backend()
        return self._model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """返回文档的 dense embedding。"""
        if not texts:
            return []
        model = self.get_model()
        return model.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        """返回单条 query 的 dense embedding。"""
        model = self.get_model()
        return model.embed_query(text)
