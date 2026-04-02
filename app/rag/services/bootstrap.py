"""
RAG 服务启动与缓存入口。
"""
from __future__ import annotations

import logging

from app.config.config import settings
from app.rag.factory import build_rag_service

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


def _main_test_rag_bootstrap():
    service = get_rag_service()
    if settings.rag_config.enabled:
        assert service is not None
    print("RAG bootstrap self test passed")


if __name__ == "__main__":
    _main_test_rag_bootstrap()
