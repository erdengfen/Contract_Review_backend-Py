"""文档格式归一化路由策略。

本文件只判断后续是否需要 DOC 到 DOCX 的归一化，不执行格式转换和正文解析。
"""
from __future__ import annotations

from src.agent.contracts.document import FormatNormalizationPlan


def plan_format_normalization(
    detected_file_type: str,
    raw_file_path: str,
) -> FormatNormalizationPlan:
    """根据感知到的文件类型生成后续格式处理计划。"""

    file_type = detected_file_type.lower()
    if file_type == "doc":
        return FormatNormalizationPlan(
            source_format="doc",
            target_format="docx",
            normalization_required=True,
            next_stage="format_normalization",
        )
    if file_type == "docx":
        return FormatNormalizationPlan(source_format="docx", target_format="docx", next_stage="parse_docx_pending")
    if file_type == "pdf":
        return FormatNormalizationPlan(source_format="pdf", target_format="pdf", next_stage="pdf_classification")
    return FormatNormalizationPlan(source_format=file_type or "unknown", target_format=None, next_stage="unsupported_type")


def _main_test_format_normalizer() -> None:
    """执行格式归一化策略的本文件自检。"""

    plan = plan_format_normalization("doc", "/tmp/test.doc")
    assert plan.normalization_required is True
    assert plan.next_stage == "format_normalization"


if __name__ == "__main__":
    _main_test_format_normalizer()
