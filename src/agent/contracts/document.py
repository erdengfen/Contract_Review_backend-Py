"""Agent 文档感知与解析契约。

本文件定义文件上传后的感知入参、解析结果、文档块和合同信息抽取结构。
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from src.agent.contracts.common import AgentContractModel, AgentError


class SourceLocation(AgentContractModel):
    """源文档定位结构，用于将文本块映射回原文件。"""

    file_path: str | None = Field(None, description="源文件路径。")
    contract_content_path: str | None = Field(None, description="解析后正文路径。")
    page_number: int | None = Field(None, description="页码。")
    block_index: int | None = Field(None, description="文档块序号。")
    layout_index: int | None = Field(None, description="版面元素序号。")
    start_offset: int | None = Field(None, description="纯文本起始偏移。")
    end_offset: int | None = Field(None, description="纯文本结束偏移。")
    element_type: str | None = Field(None, description="版面元素类型。")


class LayoutSensingMarker(AgentContractModel):
    """文件感知阶段的版面占位标记，不代表已经完成正文解析。"""

    file_type: str = Field(..., description="文件类型。")
    source_location: SourceLocation = Field(..., description="文件级来源定位。")
    page_number: int | None = Field(None, description="页码，感知阶段通常为空。")
    layout_index: int | None = Field(None, description="版面序号，感知阶段通常为空。")
    element_type: str = Field("file", description="感知阶段识别到的元素类型。")
    confidence: float | None = Field(None, description="感知判断置信度。")


class DocumentBlock(AgentContractModel):
    """文档块结构，用于解析、分块、RAG 和后续修订定位。"""

    block_id: str = Field(..., description="文档块唯一标识。")
    text: str = Field(..., description="文档块原始文本。")
    normalized_text: str | None = Field(None, description="清洗后的文档块文本。")
    source_location: SourceLocation | None = Field(None, description="源文档定位信息。")
    section_title: str | None = Field(None, description="所属章节标题。")
    page_number: int | None = Field(None, description="冗余页码。")
    block_index: int | None = Field(None, description="分块顺序。")
    token_count: int | None = Field(None, description="估算 token 数。")
    char_count: int | None = Field(None, description="字符数。")
    metadata: dict[str, Any] = Field(default_factory=dict, description="非敏感扩展信息。")


class ParsedDocument(AgentContractModel):
    """解析后的文档结构，用于文件感知能力返回正文和分块。"""

    filename: str = Field(..., description="上传文件名或合同标题。")
    file_type: str = Field(..., description="文件类型。")
    file_path: str | None = Field(None, description="原文件保存路径。")
    normalized_file_path: str | None = Field(None, description="格式归一后的文件路径。")
    contract_content: str | None = Field(None, description="解析出的合同正文。")
    contract_content_path: str | None = Field(None, description="正文写入路径。")
    blocks: list[DocumentBlock] = Field(default_factory=list, description="文档块列表。")
    parser_name: str | None = Field(None, description="实际使用的解析器名称。")
    parse_status: Literal["success", "partial", "failed"] = Field("success", description="解析状态。")
    warnings: list[str] = Field(default_factory=list, description="非敏感解析告警。")


class DocumentIntakeRequest(AgentContractModel):
    """文件感知请求，来源于旧上传链路保存后的文件引用。"""

    file_id: int | None = Field(None, description="backend 入库后的文件ID。")
    user_id: int | None = Field(None, description="业务用户ID，权限控制由 backend 负责。")
    filename: str = Field(..., description="上传文件名。")
    file_type: str = Field(..., description="上传文件类型。")
    save_path: str = Field(..., description="backend 提供的稳定本地或共享存储路径。")
    storage_uri: str | None = Field(None, description="backend 提供的对象存储或文件服务 URI。")


class FileReferenceSnapshot(AgentContractModel):
    """文件引用快照，记录 agent 可读取的稳定文件引用和文件级指纹。"""

    file_id: int | None = Field(None, description="backend 入库后的文件ID。")
    original_filename: str = Field(..., description="原始上传文件名。")
    declared_file_type: str = Field(..., description="backend 传入的声明文件类型。")
    detected_file_type: str = Field(..., description="agent 基于文件级线索识别出的文件类型。")
    save_path: str = Field(..., description="backend 提供的稳定本地或共享存储路径。")
    storage_uri: str | None = Field(None, description="backend 提供的对象存储或文件服务 URI。")
    size_bytes: int | None = Field(None, description="文件大小。")
    sha256: str | None = Field(None, description="文件 SHA256 指纹。")


class PromptInjectionGuardResult(AgentContractModel):
    """提示词注入防护标记，说明文件内容只能作为不可信合同材料处理。"""

    content_trust_level: Literal["untrusted_user_document"] = Field(
        "untrusted_user_document",
        description="内容信任级别。",
    )
    prompt_handling_policy: Literal["quote_only_never_instruction"] = Field(
        "quote_only_never_instruction",
        description="后续 prompt 只能引用，不能执行为指令。",
    )
    risk_flags: list[str] = Field(default_factory=list, description="提示词注入和文件名风险标记。")
    blocked: bool = Field(False, description="是否阻断进入后续处理。")


class FormatNormalizationPlan(AgentContractModel):
    """格式归一化计划，只记录策略和目标，不执行实际转换。"""

    source_format: str = Field(..., description="感知到的源格式。")
    target_format: str | None = Field(None, description="后续目标格式。")
    normalization_required: bool = Field(False, description="是否需要后续归一化。")
    next_stage: str = Field(..., description="后续处理阶段。")


class PdfPhysicalClassification(AgentContractModel):
    """PDF 物理分类结果，仅基于文件级线索做分流，不抽取正文。"""

    pdf_physical_type: Literal["text_pdf", "scanned_pdf", "unknown_pdf", "not_pdf"] = Field(
        ...,
        description="PDF 物理类型。",
    )
    route: Literal["pdf_text_extract", "pdf_ocr_required", "pdf_physical_check_required", "not_pdf"] = Field(
        ...,
        description="PDF 后续处理路由。",
    )
    confidence: float = Field(..., description="分类置信度。")
    evidence: dict[str, int] = Field(default_factory=dict, description="非敏感二进制线索计数。")


class DocumentSensingResult(AgentContractModel):
    """文件感知结果，汇总文件引用、安全标记、格式策略、PDF 分流和版面占位标记。"""

    request: DocumentIntakeRequest = Field(..., description="原始感知请求。")
    file_reference: FileReferenceSnapshot = Field(..., description="文件引用快照。")
    trust: PromptInjectionGuardResult = Field(..., description="提示词注入防护标记。")
    format_plan: FormatNormalizationPlan = Field(..., description="格式归一化策略。")
    pdf_classification: PdfPhysicalClassification | None = Field(None, description="PDF 物理分类结果。")
    layout_markers: list[LayoutSensingMarker] = Field(default_factory=list, description="版面占位标记。")
    detected_file_type: str = Field(..., description="通过文件头或后缀识别出的类型。")
    route: str = Field(..., description="后续处理路由。")
    warnings: list[str] = Field(default_factory=list, description="非敏感告警。")


class ContractInfoExtraction(AgentContractModel):
    """合同信息抽取结果，承接旧版甲方、乙方和金额字段。"""

    party_a: str | None = Field(None, description="甲方名称。")
    party_b: str | None = Field(None, description="乙方名称。")
    amount: float | None = Field(None, description="合同金额。")


class DocumentIntakeResponse(AgentContractModel):
    """文件感知响应，供 backend 创建合同文件记录和旧上传响应。"""

    parsed_document: ParsedDocument = Field(..., description="解析后的文档。")
    contract_info: ContractInfoExtraction = Field(..., description="合同信息抽取结果。")
    errors: list[AgentError] = Field(default_factory=list, description="错误和降级信息。")
    fallback_used: bool = Field(False, description="是否使用降级解析。")


def _main_test_document() -> None:
    """执行文档契约结构的本文件自检。"""

    location = SourceLocation(file_path="/tmp/contract.docx", page_number=1)
    marker = LayoutSensingMarker(file_type="docx", source_location=location, confidence=0.5)
    block = DocumentBlock(block_id="file-1-page-1-block-1", text="付款条款", source_location=location)
    parsed = ParsedDocument(filename="合同.docx", file_type="docx", blocks=[block])
    reference = FileReferenceSnapshot(
        original_filename="合同.docx",
        declared_file_type="docx",
        detected_file_type="docx",
        save_path="/tmp/contract.docx",
    )
    guard = PromptInjectionGuardResult()
    plan = FormatNormalizationPlan(source_format="docx", target_format="docx", next_stage="parse_docx")
    request = DocumentIntakeRequest(user_id=1, filename="合同.docx", file_type="docx", save_path="/tmp/contract.docx")
    sensing = DocumentSensingResult(
        request=request,
        file_reference=reference,
        trust=guard,
        format_plan=plan,
        layout_markers=[marker],
        detected_file_type="docx",
        route="parse_docx",
    )
    info = ContractInfoExtraction(party_a="甲方", party_b="乙方", amount=100.0)
    response = DocumentIntakeResponse(parsed_document=parsed, contract_info=info)
    assert sensing.layout_markers[0].element_type == "file"
    assert response.parsed_document.blocks[0].block_id == "file-1-page-1-block-1"
    assert response.contract_info.amount == 100.0


if __name__ == "__main__":
    _main_test_document()
