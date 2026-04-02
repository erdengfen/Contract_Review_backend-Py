"""
可复用的确定性假 embedding 客户端。
"""
from __future__ import annotations

import hashlib
import math


class DeterministicFakeEmbeddingClient:
    """
    生成稳定、可复现的假 embedding 向量。

    适用场景：
    - 真实 Qdrant 入库链路验证
    - 真实检索链路验证
    - 不希望触发本地模型权重下载时的结构测试
    """

    def __init__(self, dim: int = 512):
        self.dim = dim

    def _text_to_vector(self, text: str) -> list[float]:
        values: list[float] = []
        counter = 0
        while len(values) < self.dim:
            digest = hashlib.sha256(f"{text}|{counter}".encode("utf-8")).digest()
            for index in range(0, len(digest), 4):
                chunk = digest[index:index + 4]
                if len(chunk) < 4:
                    continue
                raw_value = int.from_bytes(chunk, "big", signed=False)
                normalized = (raw_value / 4294967295.0) * 2.0 - 1.0
                values.append(normalized)
                if len(values) >= self.dim:
                    break
            counter += 1

        norm = math.sqrt(sum(value * value for value in values)) or 1.0
        return [value / norm for value in values]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._text_to_vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._text_to_vector(text)


def _main_test_fake_embedding():
    client = DeterministicFakeEmbeddingClient(dim=8)
    vec1 = client.embed_query("付款条款")
    vec2 = client.embed_query("付款条款")
    vec3 = client.embed_query("违约责任")
    assert len(vec1) == 8
    assert vec1 == vec2
    assert vec1 != vec3
    print("DeterministicFakeEmbeddingClient self test passed")


if __name__ == "__main__":
    _main_test_fake_embedding()
