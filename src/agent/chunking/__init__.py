"""Agent 切片层导出。

本文件集中导出 Step 6 文档切片能力。
"""
from src.agent.chunking.semantic_chunker import DEFAULT_CHUNK_MAX_CHARS, chunk_parsed_document

__all__ = [
    "DEFAULT_CHUNK_MAX_CHARS",
    "chunk_parsed_document",
]


def _main_test_exports() -> None:
    """执行切片层导出的本文件自检。"""

    exported_names = set(__all__)
    assert "chunk_parsed_document" in exported_names


if __name__ == "__main__":
    _main_test_exports()
