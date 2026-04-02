"""
远程 reranker 客户端。
"""
from __future__ import annotations

from typing import Any

import httpx

from app.rag.config import RagRerankConfig
from app.rag.schemas import RetrievalHit


class RemoteRerankConfigError(RuntimeError):
    """远程 reranker 配置不完整时抛出。"""


class RemoteRerankClient:
    """
    通用远程 reranker 客户端。

    默认按 `/rerank` JSON 接口请求，兼容常见返回格式：
    - {"results": [{"index": 0, "relevance_score": 0.9}]}
    - {"data": [{"index": 0, "score": 0.9}]}
    """

    def __init__(self, config: RagRerankConfig):
        self.config = config
        self._client: httpx.Client | None = None

    def _validate(self):
        if not self.config.remote_base_url:
            raise RemoteRerankConfigError("缺少 reranker remote_base_url 配置。")
        if not self.config.remote_model:
            raise RemoteRerankConfigError("缺少 reranker remote_model 配置。")

    def get_client(self) -> httpx.Client:
        if self._client is None:
            self._validate()
            headers = {"Content-Type": "application/json"}
            if self.config.remote_api_key:
                headers["Authorization"] = f"Bearer {self.config.remote_api_key}"
            self._client = httpx.Client(
                base_url=self.config.remote_base_url.rstrip("/"),
                headers=headers,
                timeout=30.0,
            )
        return self._client

    def _build_payload(self, query: str, hits: list[RetrievalHit], top_n: int) -> dict[str, Any]:
        return {
            "model": self.config.remote_model,
            "query": query,
            "documents": [hit.content for hit in hits],
            "top_n": top_n,
        }

    @staticmethod
    def _extract_ranked_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
        if isinstance(payload.get("results"), list):
            return payload["results"]
        if isinstance(payload.get("data"), list):
            return payload["data"]
        return []

    def rerank(self, query: str, hits: list[RetrievalHit], top_n: int) -> list[RetrievalHit]:
        if not hits:
            return []

        response = self.get_client().post(
            "/rerank",
            json=self._build_payload(query=query, hits=hits, top_n=top_n),
        )
        response.raise_for_status()
        payload = response.json()
        ranked_items = self._extract_ranked_items(payload)
        if not ranked_items:
            return hits[:top_n]

        reranked_hits: list[RetrievalHit] = []
        for item in ranked_items:
            index = item.get("index")
            if index is None or not (0 <= index < len(hits)):
                continue
            hit = hits[index].model_copy(deep=True)
            if "relevance_score" in item:
                hit.score = float(item["relevance_score"])
            elif "score" in item:
                hit.score = float(item["score"])
            reranked_hits.append(hit)
        return reranked_hits[:top_n]

    def close(self):
        if self._client is not None:
            self._client.close()
        self._client = None


class _FakeResponse:
    def __init__(self, payload: dict[str, Any]):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeHttpClient:
    def post(self, path: str, json: dict[str, Any]):
        documents = json["documents"]
        scored = []
        for idx, doc in enumerate(documents):
            score = 1.0 if "违约" in doc else 0.5
            scored.append({"index": idx, "score": score})
        scored.sort(key=lambda item: item["score"], reverse=True)
        return _FakeResponse({"results": scored[: json["top_n"]]})

    def close(self):
        return None


class _TestableRemoteRerankClient(RemoteRerankClient):
    def get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = _FakeHttpClient()
        return self._client


def _main_test_remote_rerank():
    config = RagRerankConfig(
        remote_base_url="http://fake-rerank-service",
        remote_model="bge-reranker-v2-m3",
    )
    client = _TestableRemoteRerankClient(config)
    hits = [
        RetrievalHit(
            source_collection="internal_review_rules",
            record_id="rule-1",
            title="付款条款规则",
            content="付款条款必须明确付款期限。",
            score=0.2,
        ),
        RetrievalHit(
            source_collection="internal_review_rules",
            record_id="rule-2",
            title="违约责任规则",
            content="违约责任条款必须量化违约金。",
            score=0.1,
        ),
    ]
    reranked = client.rerank("违约责任", hits, top_n=1)
    assert len(reranked) == 1
    assert reranked[0].record_id == "rule-2"
    print("RemoteRerankClient self test passed")


if __name__ == "__main__":
    _main_test_remote_rerank()
