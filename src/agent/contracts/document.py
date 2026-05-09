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

    user_id: int = Field(..., description="上传用户ID。")
    filename: str = Field(..., description="上传文件名。")
    file_type: str = Field(..., description="上传文件类型。")
    save_path: str = Field(..., description="文件保存路径。")
    expected_contract_content_path: str | None = Field(None, description="backend 期望的正文写入路径。")


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
    block = DocumentBlock(block_id="file-1-page-1-block-1", text="付款条款", source_location=location)
    parsed = ParsedDocument(filename="合同.docx", file_type="docx", blocks=[block])
    info = ContractInfoExtraction(party_a="甲方", party_b="乙方", amount=100.0)
    response = DocumentIntakeResponse(parsed_document=parsed, contract_info=info)
    assert response.parsed_document.blocks[0].block_id == "file-1-page-1-block-1"
    assert response.contract_info.amount == 100.0


if __name__ == "__main__":
    _main_test_document()
