"""
Qdrant 初始化与连通验证入口。
"""
from __future__ import annotations

import argparse
import json
from typing import Any

from app.config.config import settings
from app.rag.clients.qdrant_client import RagQdrantClient
from app.rag.config import RagConfig


class QdrantSetupService:
    """
    负责 Qdrant 连通性检查和默认 collection 初始化。
    """

    def __init__(self, config: RagConfig, qdrant_client: Any | None = None):
        self.config = config
        self.qdrant_client = qdrant_client or RagQdrantClient(config.qdrant)

    def validate_connection(self) -> dict[str, Any]:
        connected = self.qdrant_client.ping()
        return {
            "connected": connected,
            "host": self.config.qdrant.host,
            "port": self.config.qdrant.port,
            "external_collection": self.config.qdrant.external_collection,
            "internal_collection": self.config.qdrant.internal_collection,
        }

    def ensure_collections(self, recreate: bool = False) -> dict[str, Any]:
        result = self.qdrant_client.ensure_default_collections(recreate=recreate)
        return {
            "dense_vector_size": self.config.qdrant.dense_vector_size,
            "collections": result,
        }

    def inspect_collections(self) -> dict[str, Any]:
        names = [
            self.config.qdrant.external_collection,
            self.config.qdrant.internal_collection,
        ]
        info = {}
        for name in names:
            exists = self.qdrant_client.collection_exists(name)
            info[name] = {
                "exists": exists,
                "info": self.qdrant_client.get_collection_info(name) if exists else None,
            }
        return info

    def bootstrap(self, recreate: bool = False) -> dict[str, Any]:
        connection = self.validate_connection()
        collections = self.ensure_collections(recreate=recreate)
        inspection = self.inspect_collections()
        return {
            "connection": connection,
            "collections": collections,
            "inspection": inspection,
        }


class _FakeSetupClient:
    def __init__(self):
        self.collections = set()

    def ping(self) -> bool:
        return True

    def ensure_default_collections(self, recreate: bool = False) -> dict[str, bool]:
        self.collections.add("external_legal_kb")
        self.collections.add("internal_review_rules")
        return {
            "external_legal_kb": True,
            "internal_review_rules": True,
        }

    def collection_exists(self, name: str) -> bool:
        return name in self.collections

    def get_collection_info(self, name: str):
        return {"name": name, "status": "green"}


def _main_test_qdrant_setup():
    service = QdrantSetupService(
        config=RagConfig(),
        qdrant_client=_FakeSetupClient(),
    )
    connection = service.validate_connection()
    assert connection["connected"] is True
    result = service.bootstrap()
    assert result["collections"]["collections"]["external_legal_kb"] is True
    assert result["inspection"]["external_legal_kb"]["exists"] is True
    assert result["inspection"]["internal_review_rules"]["exists"] is True
    print("QdrantSetupService self test passed")


def _run_real_bootstrap(recreate: bool = False):
    service = QdrantSetupService(config=settings.rag_config)
    result = service.bootstrap(recreate=recreate)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Qdrant 初始化与连通验证入口")
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="执行文件内自测，不连接真实 Qdrant。",
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="重建默认双 collection。",
    )
    args = parser.parse_args()

    if args.self_test:
        _main_test_qdrant_setup()
    else:
        _run_real_bootstrap(recreate=args.recreate)
