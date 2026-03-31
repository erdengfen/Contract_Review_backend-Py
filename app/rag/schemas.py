"""
RAG 知识记录、检索请求和检索结果 schema。
"""
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


SourceType = Literal[
    "law",
    "judicial_interpretation",
    "industry_regulation",
    "local_regulation",
]

SourceLevel = Literal[
    "national",
    "ministerial",
    "provincial",
    "municipal",
    "industry",
]

RuleType = Literal[
    "review_rule",
    "risk_rule",
    "label_rule",
    "drafting_guideline",
]


class ExternalLegalRecord(BaseModel):
    doc_id: str = Field(..., description="法律文本切片唯一 ID。")
    source_type: SourceType = Field(..., description="法律来源类型。")
    source_level: SourceLevel = Field(..., description="法律来源层级。")
    title: str = Field(..., description="法规或文件标题。")
    article_no: str = Field(..., description="条号或款项编号。")
    content: str = Field(..., description="切片正文内容。")
    region: str = Field(..., description="适用地区。")
    industry: list[str] = Field(default_factory=list, description="适用行业列表。")
    effective_status: str = Field(..., description="生效状态。")
    contract_type_tags: list[str] = Field(default_factory=list, description="适用合同类型标签。")
    risk_tags: list[str] = Field(default_factory=list, description="适用风险标签。")
    payload: dict[str, Any] = Field(default_factory=dict, description="扩展 payload 字段。")


class InternalRuleRecord(BaseModel):
    rule_id: str = Field(..., description="内部规则唯一 ID。")
    rule_type: RuleType = Field(..., description="内部规则类型。")
    title: str = Field(..., description="规则标题。")
    content: str = Field(..., description="规则内容。")
    organization_scope: str = Field(..., description="组织适用范围。")
    contract_type_tags: list[str] = Field(default_factory=list, description="适用合同类型标签。")
    risk_tags: list[str] = Field(default_factory=list, description="适用风险标签。")
    priority: int = Field(..., description="规则优先级。")
    enabled: bool = Field(..., description="规则是否启用。")
    payload: dict[str, Any] = Field(default_factory=dict, description="扩展 payload 字段。")


class RagFilters(BaseModel):
    region: Optional[str] = Field(None, description="地区过滤条件。")
    industry: Optional[str] = Field(None, description="行业过滤条件。")
    contract_type: Optional[str] = Field(None, description="合同类型过滤条件。")
    risk_tags: list[str] = Field(default_factory=list, description="风险标签过滤条件。")
    organization_scope: Optional[str] = Field(None, description="组织范围过滤条件。")


class RetrievalRequest(BaseModel):
    chunk_text: str = Field(..., description="当前待审阅 chunk 文本。")
    contract_type: Optional[str] = Field(None, description="当前合同类型。")
    stance: Optional[str] = Field(None, description="审阅立场。")
    legal_issue_query: Optional[str] = Field(None, description="归一化后的法律问题 query。")
    risk_tag_query: Optional[str] = Field(None, description="归一化后的风险标签 query。")
    filters: RagFilters = Field(default_factory=RagFilters, description="检索过滤条件。")


class RetrievalHit(BaseModel):
    source_collection: Literal["external_legal_kb", "internal_review_rules"] = Field(
        ...,
        description="命中来源 collection。",
    )
    record_id: str = Field(..., description="来源记录 ID。")
    title: str = Field(..., description="命中结果标题。")
    content: str = Field(..., description="命中结果正文。")
    score: float = Field(..., description="融合后的最终分数。")
    article_no: Optional[str] = Field(None, description="法律来源的条号。")
    rule_type: Optional[str] = Field(None, description="内部规则的规则类型。")
    source_type: Optional[str] = Field(None, description="法律来源类型。")
    payload: dict[str, Any] = Field(default_factory=dict, description="关联 payload。")


class RetrievalResponse(BaseModel):
    external_hits: list[RetrievalHit] = Field(default_factory=list, description="外部法律命中结果。")
    internal_hits: list[RetrievalHit] = Field(default_factory=list, description="内部规则命中结果。")
    fused_hits: list[RetrievalHit] = Field(default_factory=list, description="融合后的全部结果。")
    prompt_context: str = Field("", description="可直接注入 prompt 的检索上下文。")


def _main_test_schemas():
    external = ExternalLegalRecord(
        doc_id="law-1",
        source_type="law",
        source_level="national",
        title="民法典",
        article_no="第五百零九条",
        content="当事人应当按照约定全面履行自己的义务。",
        region="CN",
        effective_status="effective",
    )
    internal = InternalRuleRecord(
        rule_id="rule-1",
        rule_type="review_rule",
        title="付款条款规则",
        content="付款条款应明确付款条件与付款期限。",
        organization_scope="global",
        priority=10,
        enabled=True,
    )
    request = RetrievalRequest(chunk_text="测试合同条款")
    hit = RetrievalHit(
        source_collection="external_legal_kb",
        record_id=external.doc_id,
        title=external.title,
        content=external.content,
        score=0.95,
        article_no=external.article_no,
        source_type=external.source_type,
    )
    response = RetrievalResponse(
        external_hits=[hit],
        fused_hits=[hit],
        prompt_context="## 外部法律依据\n1. 民法典 第五百零九条",
    )
    assert request.chunk_text == "测试合同条款"
    assert internal.enabled is True
    assert response.external_hits[0].title == "民法典"
    print("RAG schemas self test passed")


if __name__ == "__main__":
    _main_test_schemas()
