"""文档感知层编排入口。

本文件整合存储安全、格式策略、PDF 分流和版面占位标记，不执行正文解析、格式转换或 OCR。
"""
from __future__ import annotations

from src.agent.contracts.document import DocumentIntakeRequest, DocumentSensingResult, PdfPhysicalClassification
from src.agent.document_intake.format_normalizer import plan_format_normalization
from src.agent.document_intake.layout_mapping import build_initial_layout_marker
from src.agent.document_intake.pdf_classifier import classify_pdf_physical_type
from src.agent.document_intake.storage_guard import (
    build_file_reference_snapshot,
    build_prompt_injection_guard,
    detect_file_type,
    get_declared_file_type,
)


def sense_document(request: DocumentIntakeRequest) -> DocumentSensingResult:
    """执行文件感知，输出安全、格式、分流和占位标记结果。"""

    declared_type = get_declared_file_type(request)
    detected_type = detect_file_type(request.save_path, declared_type)
    file_reference = build_file_reference_snapshot(request, detected_type)
    trust = build_prompt_injection_guard(request, detected_type)
    format_plan = plan_format_normalization(detected_type, file_reference.save_path)
    pdf_classification = _classify_pdf_if_needed(file_reference.save_path, detected_type)
    route = _choose_route(trust.blocked, format_plan.next_stage, pdf_classification.route if pdf_classification else None)
    marker = build_initial_layout_marker(
        file_path=file_reference.save_path,
        file_type=detected_type,
        confidence=pdf_classification.confidence if pdf_classification else None,
    )
    return DocumentSensingResult(
        request=request,
        file_reference=file_reference,
        trust=trust,
        format_plan=format_plan,
        pdf_classification=pdf_classification,
        layout_markers=[marker],
        detected_file_type=detected_type,
        route=route,
        warnings=_build_warnings(declared_type, detected_type, trust.blocked),
    )


def _classify_pdf_if_needed(
    raw_file_path: str,
    detected_type: str,
) -> PdfPhysicalClassification | None:
    """仅对 PDF 生成物理分类结果。"""

    if detected_type != "pdf":
        return None
    return classify_pdf_physical_type(raw_file_path, detected_type)


def _choose_route(
    blocked: bool,
    format_next_stage: str,
    pdf_route: str | None,
) -> str:
    """根据阻断状态、格式策略和 PDF 分类结果选择后续路由。"""

    if blocked:
        return "blocked"
    if format_next_stage == "format_normalization":
        return "format_normalization_required"
    if pdf_route:
        return pdf_route
    return format_next_stage


def _build_warnings(
    declared_type: str,
    detected_type: str,
    blocked: bool,
) -> list[str]:
    """生成非敏感告警。"""

    warnings = []
    if declared_type != detected_type:
        warnings.append("declared_type_mismatch")
    if blocked:
        warnings.append("document_sensing_blocked")
    return warnings


def _main_test_sensing() -> None:
    """执行文档感知编排的本文件自检。"""

    request = DocumentIntakeRequest(user_id=1, filename="missing.pdf", file_type="pdf", save_path="/missing.pdf")
    result = sense_document(request)
    assert result.route == "blocked"
    assert result.detected_file_type == "pdf"
    assert result.trust.blocked is True


if __name__ == "__main__":
    _main_test_sensing()
