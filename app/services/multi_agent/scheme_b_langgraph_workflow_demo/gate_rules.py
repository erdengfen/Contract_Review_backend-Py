"""方案 B 的 Gate 规则。"""

from __future__ import annotations

from collections import Counter
from difflib import SequenceMatcher

from .graph_state import DisputedFinding, MergedFinding, RuleHit

PLACEHOLDER_TOKENS = ("本块原文中的问题", "修改建议", "未找到修改建议", "结构化解析失败")
GENERIC_SUGGESTION_TOKENS = ("建议进一步明确", "建议补充约定", "建议协商", "建议关注", "建议评估")
SUMMARY_TITLE_TOKENS = ("总结", "核心风险", "行动建议")


def run_gate_1(findings: list[MergedFinding]) -> tuple[list[MergedFinding], list[DisputedFinding]]:
    """Gate-1：完整性与合规性。"""
    passed: list[MergedFinding] = []
    blocked: list[DisputedFinding] = []
    for finding in findings:
        rule_hits: list[RuleHit] = []
        reasons: list[str] = []
        combined_text = " ".join(
            [finding["title"], finding["issue"], finding["suggestion"], finding["evidence"]]
        )

        if any(token in combined_text for token in PLACEHOLDER_TOKENS):
            reasons.append("命中占位文本规则")
            rule_hits.append(_rule_hit("GATE1-PLACEHOLDER-001", "BLOCKER", "FAIL", "输出包含占位文本"))

        if finding["risk_level"] == "高" and not finding["evidence"].strip():
            reasons.append("高风险结论缺少证据")
            rule_hits.append(_rule_hit("GATE1-HIGH-EVIDENCE-001", "BLOCKER", "FAIL", "高风险结论必须提供证据"))

        if finding["risk_level"] in {"高", "中"} and not finding["source_chunk_ids"]:
            reasons.append("中高风险结论缺少证据锚点")
            rule_hits.append(_rule_hit("GATE1-ANCHOR-001", "BLOCKER", "FAIL", "中高风险结论必须提供 chunk 锚点"))

        if reasons:
            blocked.append(
                _to_disputed_finding(
                    finding=finding,
                    gate_name="Gate-1",
                    stage_name="rule_gate_1",
                    rule_hits=rule_hits,
                    dispute_reason="；".join(reasons),
                )
            )
        else:
            passed.append(finding)
    return passed, blocked


def run_gate_2(
    findings: list[MergedFinding],
) -> tuple[list[MergedFinding], list[DisputedFinding], list[MergedFinding]]:
    """Gate-2：一致性与质量。"""
    accepted: list[MergedFinding] = []
    blocked: list[DisputedFinding] = []
    suppressed: list[MergedFinding] = []
    retained: list[MergedFinding] = []

    for finding in findings:
        duplicate_reason = _find_duplicate_reason(finding, retained)
        if duplicate_reason:
            suppressed.append(finding)
            continue

        rule_hits: list[RuleHit] = []
        reasons: list[str] = []
        normalized_suggestion = _normalize(finding["suggestion"])
        normalized_evidence = _normalize(finding["evidence"])

        if len(normalized_evidence) < 18 and finding["risk_level"] in {"高", "中"}:
            reasons.append("中高风险证据摘要过短")
            rule_hits.append(_rule_hit("GATE2-EVIDENCE-WEAK-001", "MAJOR", "FAIL", "中高风险证据摘要过短"))

        if not normalized_suggestion:
            reasons.append("修改建议为空")
            rule_hits.append(_rule_hit("GATE2-SUGGESTION-EMPTY-001", "BLOCKER", "FAIL", "修改建议不能为空"))
        elif len(normalized_suggestion) < 16 or any(
            token in finding["suggestion"] for token in GENERIC_SUGGESTION_TOKENS
        ):
            reasons.append("修改建议过于空泛")
            rule_hits.append(_rule_hit("GATE2-SUGGESTION-GENERIC-001", "MAJOR", "FAIL", "修改建议缺少可执行细节"))

        if "**" in finding["title"] or any(token in finding["title"] for token in SUMMARY_TITLE_TOKENS):
            reasons.append("标题更像总结性内容")
            rule_hits.append(_rule_hit("GATE2-SUMMARY-TITLE-001", "MAJOR", "FAIL", "标题不应为总结性段落"))

        if reasons:
            blocked.append(
                _to_disputed_finding(
                    finding=finding,
                    gate_name="Gate-2",
                    stage_name="rule_gate_2",
                    rule_hits=rule_hits,
                    dispute_reason="；".join(reasons),
                )
            )
        else:
            retained.append(finding)
            accepted.append(finding)

    return accepted, blocked, suppressed


def summarize_rule_hits(disputed_findings: list[DisputedFinding]) -> dict:
    """汇总争议规则命中。"""
    gate_counter: Counter[str] = Counter()
    rule_counter: Counter[str] = Counter()
    for finding in disputed_findings:
        gate_counter[finding["gate_name"]] += 1
        for hit in finding["rule_hits"]:
            rule_counter[hit["rule_id"]] += 1
    return {
        "disputed_count": len(disputed_findings),
        "gate_distribution": dict(gate_counter),
        "rule_distribution": dict(rule_counter),
    }


def _find_duplicate_reason(finding: MergedFinding, retained: list[MergedFinding]) -> str:
    """识别重复 finding。"""
    current_title = _normalize(finding["title"])
    current_issue = _normalize(finding["issue"])
    current_evidence = _normalize(finding["evidence"])
    current_sources = set(finding["source_chunk_ids"])

    for item in retained:
        title_similarity = _similarity(current_title, _normalize(item["title"]))
        issue_similarity = _similarity(current_issue, _normalize(item["issue"]))
        evidence_similarity = _similarity(current_evidence, _normalize(item["evidence"]))
        source_overlap = bool(current_sources.intersection(item["source_chunk_ids"]))

        if current_evidence and evidence_similarity >= 0.92 and source_overlap:
            return f"与既有 finding “{item['title']}”证据高度重复"
        if title_similarity >= 0.88 and issue_similarity >= 0.8:
            return f"与既有 finding “{item['title']}”语义高度重复"
    return ""


def _to_disputed_finding(
    *,
    finding: MergedFinding,
    gate_name: str,
    stage_name: str,
    rule_hits: list[RuleHit],
    dispute_reason: str,
) -> DisputedFinding:
    """转换为 disputed finding。"""
    return DisputedFinding(
        finding_id=finding["finding_id"],
        stage_name=stage_name,
        gate_name=gate_name,
        rule_hits=rule_hits,
        risk_level=finding["risk_level"],
        title=finding["title"],
        issue=finding["issue"],
        suggestion=finding["suggestion"],
        evidence=finding["evidence"],
        source_task_ids=finding["source_task_ids"],
        source_chunk_ids=finding["source_chunk_ids"],
        dispute_reason=dispute_reason,
        dispute_tags=[hit["rule_id"] for hit in rule_hits],
    )


def _rule_hit(rule_id: str, priority: str, result: str, message: str) -> RuleHit:
    """构造规则命中对象。"""
    return RuleHit(rule_id=rule_id, priority=priority, result=result, message=message)


def _normalize(text: str) -> str:
    """标准化文本。"""
    return "".join(str(text).split()).strip()


def _similarity(left: str, right: str) -> float:
    """计算文本相似度。"""
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()
