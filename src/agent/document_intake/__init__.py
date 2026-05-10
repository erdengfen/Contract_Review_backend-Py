"""Agent 文档感知层导出。

本文件集中导出 Step 4 文档感知能力入口和分流工具。
"""
from src.agent.document_intake.format_normalizer import plan_format_normalization
from src.agent.document_intake.layout_mapping import build_initial_layout_marker
from src.agent.document_intake.pdf_classifier import classify_pdf_physical_type
from src.agent.document_intake.sensing import sense_document
from src.agent.document_intake.storage_guard import (
    build_file_reference_snapshot,
    build_prompt_injection_guard,
    detect_file_type,
)

__all__ = [
    "build_file_reference_snapshot",
    "build_initial_layout_marker",
    "build_prompt_injection_guard",
    "classify_pdf_physical_type",
    "detect_file_type",
    "plan_format_normalization",
    "sense_document",
]


def _main_test_exports() -> None:
    """执行文档感知层导出的本文件自检。"""

    exported_names = set(__all__)
    assert "sense_document" in exported_names
    assert "build_file_reference_snapshot" in exported_names


if __name__ == "__main__":
    _main_test_exports()
