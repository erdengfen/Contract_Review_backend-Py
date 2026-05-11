"""PDF 本地文字层提取。

本文件使用 PyMuPDF 读取普通 PDF 的 text layer，作为无网络依赖的解析基础和 MinerU 结果兜底。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz


@dataclass(frozen=True)
class PdfTextPage:
    """PDF 单页文字层结果。"""

    page_number: int
    text: str


class PdfTextLayerError(RuntimeError):
    """PDF 文字层提取失败时使用的解析层异常。"""


def extract_pdf_text_layer(file_path: str) -> list[PdfTextPage]:
    """提取 PDF 每页文字层，并保留页码。"""

    path = Path(file_path).expanduser().resolve()
    if not path.exists():
        raise PdfTextLayerError("pdf_file_missing")
    try:
        return _read_pdf_pages(path)
    except PdfTextLayerError:
        raise
    except Exception as error:
        raise PdfTextLayerError("pdf_text_layer_extract_failed") from error


def _read_pdf_pages(path: Path) -> list[PdfTextPage]:
    """读取 PDF 页面文本。"""

    pages: list[PdfTextPage] = []
    with fitz.open(path) as document:
        for page_index, page in enumerate(document, start=1):
            text = page.get_text("text").strip()
            if text:
                pages.append(PdfTextPage(page_number=page_index, text=text))
    return pages


def _main_test_pdf_text_layer() -> None:
    """执行 PDF 文字层提取的本文件自检。"""

    try:
        extract_pdf_text_layer("/tmp/missing.pdf")
    except PdfTextLayerError as error:
        assert str(error) == "pdf_file_missing"
    else:
        raise AssertionError("缺失 PDF 文件必须报错")


if __name__ == "__main__":
    _main_test_pdf_text_layer()
