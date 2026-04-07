"""方案 B 的 LangGraph 状态定义。"""

from __future__ import annotations

from operator import add
from typing import Annotated, Any, TypedDict


class IndexedChunk(TypedDict):
    """分块与索引结果。"""

    chunk_id: str
    chunk_index: int
    text: str
    keyword_tags: list[str]
    reference_tokens: list[str]


class RouterTask(TypedDict):
    """Router 派发任务。"""

    task_id: str
    chunk_id: str
    route_topics: list[str]
    target_specialists: list[str]
    priority: str
    context_handles: list[str]
    rag_query_keys: list[str]
    route_reasons: list[str]


class SpecialistFinding(TypedDict):
    """Specialist 原始结构化结论。"""

    title: str
    issue: str
    suggestion: str
    evidence: str
    risk_level: str
    route_topic: str


class SpecialistOutput(TypedDict):
    """Specialist 节点输出。"""

    task_id: str
    specialist_name: str
    findings: list[SpecialistFinding]
    raw_output: str
    status: str
    chunk_id: str
    route_topic: str


class RuleHit(TypedDict):
    """规则命中。"""

    rule_id: str
    priority: str
    result: str
    message: str


class MergedFinding(TypedDict):
    """证据归并后的 finding。"""

    finding_id: str
    title: str
    issue: str
    suggestion: str
    evidence: str
    risk_level: str
    source_task_ids: list[str]
    source_chunk_ids: list[str]
    source_specialists: list[str]
    route_topics: list[str]
    rule_hits: list[RuleHit]


class DisputedFinding(TypedDict):
    """争议结论。"""

    finding_id: str
    stage_name: str
    gate_name: str
    rule_hits: list[RuleHit]
    risk_level: str
    title: str
    issue: str
    suggestion: str
    evidence: str
    source_task_ids: list[str]
    source_chunk_ids: list[str]
    dispute_reason: str
    dispute_tags: list[str]


class ExecutionTrace(TypedDict):
    """节点执行轨迹。"""

    trace_id: str
    node_name: str
    status: str
    started_at: str
    ended_at: str
    elapsed_ms: int
    summary: str
    input_count: int
    output_count: int


class ArbitrationDecision(TypedDict):
    """仲裁摘要。"""

    decision_id: str
    title: str
    action: str
    rationale: str


class GraphState(TypedDict, total=False):
    """方案 B 图状态。"""

    run_id: str
    file_path: str
    file_type: str
    contract_text: str
    snapshot_id: str
    chunks: list[IndexedChunk]
    chunk_index_map: dict[str, int]
    evidence_snapshot: dict[str, Any]
    rag_context_refs: list[str]
    router_tasks: list[RouterTask]
    specialist_outputs: Annotated[list[SpecialistOutput], add]
    merged_findings: list[MergedFinding]
    gate1_findings: list[MergedFinding]
    gate1_blocked_findings: list[DisputedFinding]
    arbitrated_findings: list[MergedFinding]
    arbitration_decisions: list[ArbitrationDecision]
    accepted_findings: list[MergedFinding]
    gate2_blocked_findings: list[DisputedFinding]
    disputed_findings: list[DisputedFinding]
    suppressed_findings: list[MergedFinding]
    execution_trace: Annotated[list[ExecutionTrace], add]
    routing_summary: dict[str, Any]
    rule_summary: dict[str, Any]
    elapsed_seconds: float
    result_file_path: str
    result_json_path: str
