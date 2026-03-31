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
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except ImportError as exc:
            raise LocalEmbeddingDependencyError(
                "缺少 sentence-transformers 依赖，无法加载本地 embedding 模型。"
            ) from exc

        return SentenceTransformer(
            self.config.local_model_name,
            device=self.config.local_device,
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
        embeddings = model.encode(
            texts,
            batch_size=self.config.local_batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        """返回单条 query 的 dense embedding。"""
        model = self.get_model()
        embedding = model.encode(
            [text],
            batch_size=1,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embedding[0].tolist()


class _FakeSentenceTransformer:
    def encode(
        self,
        sentences,
        batch_size: int = 32,
        convert_to_numpy: bool = True,
        normalize_embeddings: bool = True,
        show_progress_bar: bool = False,
    ):
        import numpy as np

        if isinstance(sentences, str):
            sentences = [sentences]
        values = []
        for idx, _ in enumerate(sentences, start=1):
            values.append([float(idx), float(idx + 1), float(idx + 2)])
        return np.array(values, dtype=float)


class _TestableLocalEmbeddingClient(LocalEmbeddingClient):
    def _load_backend(self):
        return _FakeSentenceTransformer()


def _main_test_local_embedding():
    config = RagEmbeddingConfig()
    client = _TestableLocalEmbeddingClient(config)
    docs = client.embed_documents(["甲方付款", "违约责任"])
    query = client.embed_query("付款条款")
    assert len(docs) == 2
    assert len(docs[0]) == 3
    assert len(query) == 3
    print("LocalEmbeddingClient self test passed")


if __name__ == "__main__":
    _main_test_local_embedding()
