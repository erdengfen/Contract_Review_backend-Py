"""PDF 物理类型轻量分流。

本文件只基于 PDF 二进制标记做扫描件和普通 PDF 的路由判断，不抽取正文、不执行 OCR。
"""
from __future__ import annotations

from pathlib import Path

from src.agent.contracts.document import PdfPhysicalClassification

PDF_SCAN_BYTES_LIMIT = 1024 * 1024


def classify_pdf_physical_type(
    file_path: str,
    detected_file_type: str,
) -> PdfPhysicalClassification:
    """根据二进制线索判断 PDF 后续应进入文字解析还是 OCR 路由。"""

    if detected_file_type != "pdf":
        return PdfPhysicalClassification(pdf_physical_type="not_pdf", route="not_pdf", confidence=1.0)
    sample = _read_pdf_sample(file_path)
    if not sample:
        return _unknown_pdf_classification(confidence=0.0)
    evidence = _count_pdf_markers(sample)
    return _classify_pdf_evidence(evidence)


def _classify_pdf_evidence(
    evidence: dict[str, int],
) -> PdfPhysicalClassification:
    """根据已统计的二进制线索生成 PDF 分类。"""

    if evidence["text_markers"] > 0 and evidence["text_markers"] >= evidence["image_markers"]:
        return PdfPhysicalClassification(pdf_physical_type="text_pdf", route="pdf_text_extract", confidence=0.75, evidence=evidence)
    if evidence["image_markers"] > 0 and evidence["text_markers"] == 0:
        return PdfPhysicalClassification(pdf_physical_type="scanned_pdf", route="pdf_ocr_required", confidence=0.7, evidence=evidence)
    return _unknown_pdf_classification(confidence=0.4, evidence=evidence)


def _unknown_pdf_classification(
    confidence: float,
    evidence: dict[str, int] | None = None,
) -> PdfPhysicalClassification:
    """生成未知 PDF 分类结果。"""

    return PdfPhysicalClassification(
        pdf_physical_type="unknown_pdf",
        route="pdf_physical_check_required",
        confidence=confidence,
        evidence=evidence or {},
    )


def _read_pdf_sample(file_path: str) -> bytes:
    """读取 PDF 文件头部样本，不进行正文解析。"""

    path = Path(file_path)
    if not path.exists():
        return b""
    with path.open("rb") as file_obj:
        return file_obj.read(PDF_SCAN_BYTES_LIMIT)


def _count_pdf_markers(sample: bytes) -> dict[str, int]:
    """统计 PDF 中常见文本层和图片层标记。"""

    text_markers = sample.count(b"/Font") + sample.count(b"BT") + sample.count(b"/ToUnicode")
    image_markers = sample.count(b"/Image") + sample.count(b"/XObject") + sample.count(b"/DCTDecode")
    return {"text_markers": text_markers, "image_markers": image_markers}


def _main_test_pdf_classifier() -> None:
    """执行 PDF 分类模块的本文件自检。"""

    result = classify_pdf_physical_type("/missing.pdf", "pdf")
    assert result.pdf_physical_type == "unknown_pdf"
    assert result.route == "pdf_physical_check_required"


if __name__ == "__main__":
    _main_test_pdf_classifier()
