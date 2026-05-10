"""文档感知阶段版面占位标记。

本文件只生成文件级来源定位，不做页码、表格、图片和正文解析。
"""
from __future__ import annotations

from src.agent.contracts.document import LayoutSensingMarker, SourceLocation


def build_initial_layout_marker(
    file_path: str,
    file_type: str,
    contract_content_path: str | None = None,
    confidence: float | None = None,
) -> LayoutSensingMarker:
    """构建文件级版面占位标记，供后续解析阶段补充页码和版面序号。"""

    source_location = SourceLocation(
        file_path=file_path,
        contract_content_path=contract_content_path,
        element_type="file",
    )
    return LayoutSensingMarker(file_type=file_type, source_location=source_location, confidence=confidence)


def _main_test_layout_mapping() -> None:
    """执行版面占位标记的本文件自检。"""

    marker = build_initial_layout_marker("/tmp/test.pdf", "pdf", confidence=0.5)
    assert marker.source_location.file_path == "/tmp/test.pdf"
    assert marker.element_type == "file"


if __name__ == "__main__":
    _main_test_layout_mapping()
