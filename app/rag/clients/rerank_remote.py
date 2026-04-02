"""
远程 reranker 客户端。
"""
from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
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

    def _ensure_local_no_proxy(self):
        host = urlparse(self.config.remote_base_url).hostname
        if host not in {"localhost", "127.0.0.1", "0.0.0.0"}:
            return

        for env_key in ("NO_PROXY", "no_proxy"):
            current_value = os.environ.get(env_key, "").strip()
            entries = [item.strip() for item in current_value.split(",") if item.strip()]
            changed = False
            for item in ("127.0.0.1", "localhost"):
                if item not in entries:
                    entries.append(item)
                    changed = True
            if changed:
                os.environ[env_key] = ",".join(entries)

    def get_client(self) -> httpx.Client:
        if self._client is None:
            self._validate()
            self._ensure_local_no_proxy()
            headers = {"Content-Type": "application/json"}
            if self.config.remote_api_key:
                headers["Authorization"] = f"Bearer {self.config.remote_api_key}"
            self._client = httpx.Client(
                headers=headers,
                timeout=float(self.config.remote_timeout),
            )
        return self._client

    def _build_request_url(self) -> str:
        return f"{self.config.remote_base_url.rstrip('/')}/{self.config.remote_path.lstrip('/')}"

    def _build_documents(self, hits: list[RetrievalHit]) -> list[Any]:
        if self.config.remote_provider == "siliconflow":
            return [hit.content for hit in hits]

        return [
            {
                "id": hit.record_id,
                "text": hit.content,
                "title": hit.title,
                "metadata": {
                    "source_collection": hit.source_collection,
                    "article_no": hit.article_no,
                    "rule_type": hit.rule_type,
                    "source_type": hit.source_type,
                },
            }
            for hit in hits
        ]

    def _build_payload(self, query: str, hits: list[RetrievalHit], top_n: int) -> dict[str, Any]:
        return {
            "model": self.config.remote_model,
            "query": query,
            "documents": self._build_documents(hits),
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
            self._build_request_url(),
            json=self._build_payload(query=query, hits=hits, top_n=top_n),
        )
        response.raise_for_status()
        payload = response.json()
        ranked_items = self._extract_ranked_items(payload)
        if not ranked_items:
            return hits[:top_n]

        reranked_hits: list[RetrievalHit] = []
        for item in ranked_items:
            hit = self._resolve_hit(item, hits)
            if hit is None:
                continue
            hit = hit.model_copy(deep=True)
            if "relevance_score" in item:
                hit.score = float(item["relevance_score"])
            elif "score" in item:
                hit.score = float(item["score"])
            reranked_hits.append(hit)
        return reranked_hits[:top_n]

    @staticmethod
    def _resolve_hit(item: dict[str, Any], hits: list[RetrievalHit]) -> RetrievalHit | None:
        index = item.get("index")
        if isinstance(index, int) and 0 <= index < len(hits):
            return hits[index]

        record_id = item.get("id") or item.get("document_id")
        if record_id is not None:
            for hit in hits:
                if hit.record_id == str(record_id):
                    return hit
        return None

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
            if isinstance(doc, str):
                text = doc
                record_id = str(idx)
            else:
                text = doc["text"]
                record_id = doc["id"]
            score = 1.0 if "违约" in text else 0.5
            scored.append({"index": idx, "id": record_id, "score": score})
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
        remote_model="Qwen/Qwen3-Reranker-8B",
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


class _SimpleRerankHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        documents = payload["documents"]
        results = []
        for idx, doc in enumerate(documents):
            text = doc if isinstance(doc, str) else doc["text"]
            record_id = str(idx) if isinstance(doc, str) else doc["id"]
            score = 10.0 if "违约" in text else 1.0
            results.append({"index": idx, "id": record_id, "relevance_score": score})
        results.sort(key=lambda item: item["relevance_score"], reverse=True)
        body = json.dumps({"results": results[: payload["top_n"]]}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return None


def _main_test_remote_rerank_http():
    try:
        server = ThreadingHTTPServer(("127.0.0.1", 0), _SimpleRerankHandler)
    except PermissionError:
        print("RemoteRerankClient http self test skipped: 当前环境不允许监听本地端口")
        return
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        config = RagRerankConfig(
            remote_base_url=f"http://127.0.0.1:{server.server_address[1]}",
            remote_model="Qwen/Qwen3-Reranker-8B",
        )
        client = RemoteRerankClient(config)
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
        print("RemoteRerankClient http self test passed")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    _main_test_remote_rerank()
    _main_test_remote_rerank_http()
