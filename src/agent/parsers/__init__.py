"""Agent 文档解析层导出。

本文件集中导出 Step 5 解析能力入口，供 agent 编排层调用。
"""
from src.agent.parsers.doc_normalizer import DocNormalizationError, normalize_doc_to_docx
from src.agent.parsers.docx_parser import parse_docx_file
from src.agent.parsers.document_parser import parse_document_from_sensing

__all__ = [
    "DocNormalizationError",
    "normalize_doc_to_docx",
    "parse_document_from_sensing",
    "parse_docx_file",
]


def _main_test_exports() -> None:
    """执行解析层导出的本文件自检。"""

    exported_names = set(__all__)
    assert "parse_docx_file" in exported_names
    assert "parse_document_from_sensing" in exported_names


if __name__ == "__main__":
    _main_test_exports()
