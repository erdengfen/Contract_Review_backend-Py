"""
RAG 服务启动与缓存入口。
"""
from __future__ import annotations

import logging
from typing import Any, Callable

from app.config.config import settings
from app.rag.factory import build_rag_service
from app.rag.services.qdrant_setup import QdrantSetupService

logger = logging.getLogger(__name__)

_RAG_SERVICE = None


def get_rag_service():
    """
    获取缓存后的 RAG 服务实例。
    """
    global _RAG_SERVICE
    if not settings.rag_config.enabled:
        return None

    if _RAG_SERVICE is None:
        try:
            _RAG_SERVICE = build_rag_service(settings.rag_config)
        except Exception as exc:
            logger.warning(f"初始化 RAG 服务失败，自动降级为无 RAG 模式: {exc}")
            _RAG_SERVICE = None
    return _RAG_SERVICE


def initialize_rag_runtime(
    *,
    qdrant_setup_factory: Callable[[], Any] | None = None,
    rag_service_getter: Callable[[], Any] | None = None,
) -> dict[str, Any]:
    """
    在应用启动阶段执行 RAG 健康检查，并预热服务实例。
    """
    result: dict[str, Any] = {
        "enabled": settings.rag_config.enabled,
        "startup_enabled": settings.rag_config.startup.enabled,
        "qdrant": None,
        "rag_service_ready": False,
    }
    if not settings.rag_config.enabled or not settings.rag_config.startup.enabled:
        return result

    qdrant_setup_factory = qdrant_setup_factory or (lambda: QdrantSetupService(config=settings.rag_config))
    rag_service_getter = rag_service_getter or get_rag_service

    try:
        setup_service = qdrant_setup_factory()
        connection = setup_service.validate_connection()
        result["qdrant"] = {"connection": connection}
        if not connection.get("connected"):
            raise RuntimeError(
                f"Qdrant 不可达: {connection.get('host')}:{connection.get('port')}"
            )

        if settings.rag_config.startup.ensure_qdrant_collections:
            result["qdrant"]["collections"] = setup_service.ensure_collections(recreate=False)
        result["qdrant"]["inspection"] = setup_service.inspect_collections()

        result["rag_service_ready"] = rag_service_getter() is not None
        if not result["rag_service_ready"]:
            raise RuntimeError("RAG 服务初始化失败。")
        return result
    except Exception as exc:
        result["error"] = str(exc)
        if settings.rag_config.startup.fail_fast:
            raise
        logger.warning(f"RAG 启动检查失败，保持服务降级运行: {exc}")
        return result


class _FakeBootstrapSetupService:
    def validate_connection(self) -> dict[str, Any]:
        return {
            "connected": True,
            "host": "localhost",
            "port": 6333,
            "external_collection": "external_legal_kb",
            "internal_collection": "internal_review_rules",
        }

    def ensure_collections(self, recreate: bool = False) -> dict[str, Any]:
        return {
            "dense_vector_size": 512,
            "collections": {
                "external_legal_kb": True,
                "internal_review_rules": True,
            },
        }

    def inspect_collections(self) -> dict[str, Any]:
        return {
            "external_legal_kb": {"exists": True, "info": {"status": "green"}},
            "internal_review_rules": {"exists": True, "info": {"status": "green"}},
        }


def _main_test_rag_bootstrap():
    result = initialize_rag_runtime(
        qdrant_setup_factory=lambda: _FakeBootstrapSetupService(),
        rag_service_getter=lambda: object(),
    )
    assert result["qdrant"]["connection"]["connected"] is True
    assert result["rag_service_ready"] is True
    print("RAG bootstrap self test passed")


if __name__ == "__main__":
    _main_test_rag_bootstrap()
