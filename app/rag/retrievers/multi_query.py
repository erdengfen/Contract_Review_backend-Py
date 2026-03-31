"""
多路 query 构造模块。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.rag.schemas import RetrievalRequest


RISK_KEYWORD_MAP: dict[str, tuple[str, ...]] = {
    "付款条款": ("付款", "支付", "价款", "结算", "发票"),
    "违约责任": ("违约", "赔偿", "损失", "违约金", "责任"),
    "争议解决": ("仲裁", "诉讼", "管辖", "法院", "争议"),
    "保密义务": ("保密", "秘密", "披露", "信息安全"),
    "知识产权": ("知识产权", "著作权", "专利", "商标", "成果归属"),
    "解除终止": ("解除", "终止", "退出", "解约"),
}


@dataclass(slots=True)
class MultiQueryBundle:
    raw_chunk_query: str
    legal_issue_query: str
    risk_tag_query: str
    risk_tags: list[str] = field(default_factory=list)


class MultiQueryBuilder:
    """
    将待审阅 chunk 转为多路检索 query。
    """

    def extract_risk_tags(self, text: str) -> list[str]:
        tags: list[str] = []
        lowered = text.strip()
        for tag, keywords in RISK_KEYWORD_MAP.items():
            if any(keyword in lowered for keyword in keywords):
                tags.append(tag)
        return tags

    def build_legal_issue_query(self, request: RetrievalRequest, risk_tags: list[str]) -> str:
        parts = []
        if request.contract_type:
            parts.append(f"合同类型：{request.contract_type}")
        if request.stance:
            parts.append(f"审阅立场：{request.stance}")
        if risk_tags:
            parts.append("重点法律问题：" + "、".join(risk_tags))
        else:
            parts.append("重点法律问题：合同履行与风险控制")
        return "；".join(parts)

    def build_risk_tag_query(self, risk_tags: list[str]) -> str:
        if risk_tags:
            return " ".join(risk_tags)
        return "合同审阅 风险识别"

    def build_queries(self, request: RetrievalRequest) -> MultiQueryBundle:
        raw_chunk_query = re.sub(r"\s+", " ", request.chunk_text.strip())
        risk_tags = request.filters.risk_tags[:] or self.extract_risk_tags(raw_chunk_query)
        legal_issue_query = request.legal_issue_query or self.build_legal_issue_query(request, risk_tags)
        risk_tag_query = request.risk_tag_query or self.build_risk_tag_query(risk_tags)
        return MultiQueryBundle(
            raw_chunk_query=raw_chunk_query,
            legal_issue_query=legal_issue_query,
            risk_tag_query=risk_tag_query,
            risk_tags=risk_tags,
        )


def _main_test_multi_query():
    builder = MultiQueryBuilder()
    request = RetrievalRequest(
        chunk_text="甲方应在乙方开具发票后10日内付款，逾期付款应承担违约责任。",
        contract_type="服务合同",
        stance="甲方",
    )
    bundle = builder.build_queries(request)
    assert "付款条款" in bundle.risk_tags
    assert "违约责任" in bundle.risk_tags
    assert "服务合同" in bundle.legal_issue_query
    assert bundle.raw_chunk_query.startswith("甲方应在乙方开具发票后10日内付款")
    print("MultiQueryBuilder self test passed")


if __name__ == "__main__":
    _main_test_multi_query()
