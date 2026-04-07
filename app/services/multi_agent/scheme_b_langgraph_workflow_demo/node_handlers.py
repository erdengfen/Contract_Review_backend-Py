"""方案 B 的 LangGraph 节点处理器。"""

from __future__ import annotations

import asyncio
import re
import time
from collections import defaultdict
from datetime import datetime
from typing import Any
from uuid import uuid4

try:
    from ..review_toolkit import MultiAgentReviewToolkit
    from .gate_rules import run_gate_1, run_gate_2, summarize_rule_hits
    from .graph_state import (
        ArbitrationDecision,
        DisputedFinding,
        ExecutionTrace,
        GraphState,
        IndexedChunk,
        MergedFinding,
        RouterTask,
        SpecialistFinding,
        SpecialistOutput,
    )
    from .router_rules import (
        SPECIALIST_DEFINITION,
        SPECIALIST_DISPUTE,
        SPECIALIST_LIABILITY,
        SPECIALIST_PAYMENT,
        build_router_tasks,
        extract_reference_tokens,
        infer_chunk_tags,
    )
except ImportError:
    from app.services.multi_agent.review_toolkit import MultiAgentReviewToolkit
    from app.services.multi_agent.scheme_b_langgraph_workflow_demo.gate_rules import (
        run_gate_1,
        run_gate_2,
        summarize_rule_hits,
    )
    from app.services.multi_agent.scheme_b_langgraph_workflow_demo.graph_state import (
        ArbitrationDecision,
        DisputedFinding,
        ExecutionTrace,
        GraphState,
        IndexedChunk,
        MergedFinding,
        RouterTask,
        SpecialistFinding,
        SpecialistOutput,
    )
    from app.services.multi_agent.scheme_b_langgraph_workflow_demo.router_rules import (
        SPECIALIST_DEFINITION,
        SPECIALIST_DISPUTE,
        SPECIALIST_LIABILITY,
        SPECIALIST_PAYMENT,
        build_router_tasks,
        extract_reference_tokens,
        infer_chunk_tags,
    )


class SchemeBLangGraphNodeHandlers(MultiAgentReviewToolkit):
    """方案 B 节点实现。"""

    async def parse_document_node(self, state: GraphState) -> dict[str, Any]:
        """解析合同文件。"""
        started = time.perf_counter()
        parsed_contract = await self.parse_contract_file(state["file_path"])
        return {
            "file_type": parsed_contract.file_type,
            "contract_text": parsed_contract.text,
            "execution_trace": [
                self._trace(
                    node_name="parse_document",
                    started=started,
                    input_count=1,
                    output_count=1,
                    summary="合同文件解析完成",
                )
            ],
        }

    async def split_and_index_node(self, state: GraphState) -> dict[str, Any]:
        """分块与索引。"""
        started = time.perf_counter()
        chunks = self.split_contract_text(state["contract_text"])
        indexed_chunks: list[IndexedChunk] = []
        definitions: list[dict[str, str]] = []
        for index, chunk_text in enumerate(chunks, start=1):
            chunk_id = f"chunk-{index}"
            indexed_chunks.append(
                IndexedChunk(
                    chunk_id=chunk_id,
                    chunk_index=index,
                    text=chunk_text,
                    keyword_tags=infer_chunk_tags(chunk_text),
                    reference_tokens=extract_reference_tokens(chunk_text),
                )
            )
            definitions.extend(self._extract_definition_records(chunk_id, chunk_text))

        chunk_index_map = {item["chunk_id"]: item["chunk_index"] for item in indexed_chunks}
        evidence_snapshot = {
            "snapshot_id": f"snapshot-{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "definition_count": len(definitions),
            "definitions": definitions,
        }
        rag_context_refs = [
            tag
            for chunk in indexed_chunks
            for tag in [*chunk["keyword_tags"], *chunk["reference_tokens"]]
        ]
        return {
            "snapshot_id": evidence_snapshot["snapshot_id"],
            "chunks": indexed_chunks,
            "chunk_index_map": chunk_index_map,
            "evidence_snapshot": evidence_snapshot,
            "rag_context_refs": self._unique(rag_context_refs),
            "execution_trace": [
                self._trace(
                    node_name="split_and_index",
                    started=started,
                    input_count=1,
                    output_count=len(indexed_chunks),
                    summary=f"完成 {len(indexed_chunks)} 个分块与索引",
                )
            ],
        }

    async def router_node(self, state: GraphState) -> dict[str, Any]:
        """主题路由。"""
        started = time.perf_counter()
        router_tasks, routing_summary = build_router_tasks(state["chunks"])
        return {
            "router_tasks": router_tasks,
            "routing_summary": routing_summary,
            "execution_trace": [
                self._trace(
                    node_name="router",
                    started=started,
                    input_count=len(state["chunks"]),
                    output_count=len(router_tasks),
                    summary=f"路由任务数 {len(router_tasks)}",
                )
            ],
        }

    async def specialist_payment_node(self, state: GraphState) -> dict[str, Any]:
        """付款 specialist 节点。"""
        return await self._run_specialist_node(
            state=state,
            specialist_name=SPECIALIST_PAYMENT,
            focus_instruction="重点审阅付款、结算、验收与价款触发条件。",
            route_topic="payment",
        )

    async def specialist_liability_node(self, state: GraphState) -> dict[str, Any]:
        """违约 specialist 节点。"""
        return await self._run_specialist_node(
            state=state,
            specialist_name=SPECIALIST_LIABILITY,
            focus_instruction="重点审阅违约责任、赔偿、违约金、免责与索赔。",
            route_topic="liability",
        )

    async def specialist_dispute_node(self, state: GraphState) -> dict[str, Any]:
        """争议 specialist 节点。"""
        return await self._run_specialist_node(
            state=state,
            specialist_name=SPECIALIST_DISPUTE,
            focus_instruction="重点审阅争议解决、管辖、通知、解除与终止。",
            route_topic="dispute",
        )

    async def specialist_definition_node(self, state: GraphState) -> dict[str, Any]:
        """定义 specialist 节点。"""
        return await self._run_specialist_node(
            state=state,
            specialist_name=SPECIALIST_DEFINITION,
            focus_instruction="重点审阅定义项、附件回指、空白字段和异常格式。",
            route_topic="definition",
        )

    async def merge_evidence_node(self, state: GraphState) -> dict[str, Any]:
        """证据归并。"""
        started = time.perf_counter()
        merged_findings: list[MergedFinding] = []
        for output in state.get("specialist_outputs", []):
            for index, finding in enumerate(output["findings"], start=1):
                merged_findings.append(
                    MergedFinding(
                        finding_id=f"{output['task_id']}-finding-{index}",
                        title=finding["title"],
                        issue=finding["issue"],
                        suggestion=finding["suggestion"],
                        evidence=finding["evidence"],
                        risk_level=self._normalize_risk_level(finding["risk_level"]),
                        source_task_ids=[output["task_id"]],
                        source_chunk_ids=[output["chunk_id"]],
                        source_specialists=[output["specialist_name"]],
                        route_topics=[finding["route_topic"]],
                        rule_hits=[],
                    )
                )
        return {
            "merged_findings": merged_findings,
            "execution_trace": [
                self._trace(
                    node_name="merge_evidence",
                    started=started,
                    input_count=len(state.get("specialist_outputs", [])),
                    output_count=len(merged_findings),
                    summary=f"归并后 finding 数 {len(merged_findings)}",
                )
            ],
        }

    async def rule_gate_1_node(self, state: GraphState) -> dict[str, Any]:
        """Gate-1。"""
        started = time.perf_counter()
        passed, blocked = run_gate_1(state.get("merged_findings", []))
        return {
            "gate1_findings": passed,
            "gate1_blocked_findings": blocked,
            "execution_trace": [
                self._trace(
                    node_name="rule_gate_1",
                    started=started,
                    input_count=len(state.get("merged_findings", [])),
                    output_count=len(passed),
                    summary=f"Gate-1 通过 {len(passed)}，拦截 {len(blocked)}",
                )
            ],
        }

    async def arbitration_node(self, state: GraphState) -> dict[str, Any]:
        """仲裁节点。"""
        started = time.perf_counter()
        findings = state.get("gate1_findings", [])
        kept: list[MergedFinding] = []
        decisions: list[ArbitrationDecision] = []

        for finding in findings:
            target = self._find_arbitration_duplicate(finding, kept)
            if target is None:
                kept.append(finding)
                continue
            kept[target] = self._merge_findings(kept[target], finding)
            decisions.append(
                ArbitrationDecision(
                    decision_id=f"decision-{len(decisions) + 1}",
                    title=kept[target]["title"],
                    action="merge",
                    rationale="同主题且证据相近，仲裁后合并为统一口径。",
                )
            )

        return {
            "arbitrated_findings": kept,
            "arbitration_decisions": decisions,
            "execution_trace": [
                self._trace(
                    node_name="arbitration",
                    started=started,
                    input_count=len(findings),
                    output_count=len(kept),
                    summary=f"仲裁后保留 {len(kept)} 条，生成 {len(decisions)} 条决策",
                )
            ],
        }

    async def rule_gate_2_node(self, state: GraphState) -> dict[str, Any]:
        """Gate-2。"""
        started = time.perf_counter()
        accepted, blocked, suppressed = run_gate_2(state.get("arbitrated_findings", []))
        return {
            "accepted_findings": accepted,
            "gate2_blocked_findings": blocked,
            "suppressed_findings": suppressed,
            "execution_trace": [
                self._trace(
                    node_name="rule_gate_2",
                    started=started,
                    input_count=len(state.get("arbitrated_findings", [])),
                    output_count=len(accepted),
                    summary=f"Gate-2 通过 {len(accepted)}，拦截 {len(blocked)}，抑制 {len(suppressed)}",
                )
            ],
        }

    async def record_disputed_findings_node(self, state: GraphState) -> dict[str, Any]:
        """记录争议结论。"""
        started = time.perf_counter()
        disputed_findings = [
            *state.get("gate1_blocked_findings", []),
            *state.get("gate2_blocked_findings", []),
        ]
        rule_summary = summarize_rule_hits(disputed_findings)
        return {
            "disputed_findings": disputed_findings,
            "rule_summary": rule_summary,
            "execution_trace": [
                self._trace(
                    node_name="record_disputed_findings",
                    started=started,
                    input_count=len(disputed_findings),
                    output_count=len(disputed_findings),
                    summary=f"记录 disputed findings {len(disputed_findings)} 条",
                )
            ],
        }

    async def _run_specialist_node(
        self,
        *,
        state: GraphState,
        specialist_name: str,
        focus_instruction: str,
        route_topic: str,
    ) -> dict[str, Any]:
        """执行单个 specialist 节点。"""
        started = time.perf_counter()
        tasks = [
            task
            for task in state.get("router_tasks", [])
            if specialist_name in task["target_specialists"]
        ]
        if not tasks:
            return {
                "execution_trace": [
                    self._trace(
                        node_name=self._specialist_node_name(specialist_name),
                        started=started,
                        input_count=0,
                        output_count=0,
                        summary="无匹配任务，跳过",
                    )
                ]
            }

        chunk_map = {item["chunk_id"]: item for item in state.get("chunks", [])}
        semaphore = asyncio.Semaphore(self.demo_config.max_concurrent_reviews)

        async def _run_task(task: RouterTask) -> SpecialistOutput:
            chunk = chunk_map[task["chunk_id"]]
            context = (
                f"你当前扮演 {specialist_name}。\n"
                f"审阅焦点：{focus_instruction}\n"
                f"路由主题：{'/'.join(task['route_topics'])}\n"
                f"路由原因：{'；'.join(task['route_reasons'])}\n"
                f"句柄：{'；'.join(task['context_handles']) or '无'}"
            )
            async with semaphore:
                review_result = await self.review_chunk(
                    chunk_text=chunk["text"],
                    stance=self.demo_config.default_stance,
                    intensity=self.demo_config.default_intensity,
                    contract_type=self.demo_config.default_contract_type,
                    context=context,
                )
            findings = [
                SpecialistFinding(
                    title=str(item.get("risk_type", "")).strip() or specialist_name,
                    issue=str(item.get("risk_analysis", "")).strip(),
                    suggestion=str(item.get("suggested_content", "")).strip(),
                    evidence=str(item.get("original_content", "")).strip(),
                    risk_level=self._normalize_risk_level(item.get("risk_level")),
                    route_topic=route_topic,
                )
                for item in review_result
            ]
            return SpecialistOutput(
                task_id=task["task_id"],
                specialist_name=specialist_name,
                findings=findings,
                raw_output="",
                status="ok",
                chunk_id=task["chunk_id"],
                route_topic=route_topic,
            )

        specialist_outputs = await asyncio.gather(*[_run_task(task) for task in tasks])
        return {
            "specialist_outputs": specialist_outputs,
            "execution_trace": [
                self._trace(
                    node_name=self._specialist_node_name(specialist_name),
                    started=started,
                    input_count=len(tasks),
                    output_count=sum(len(item["findings"]) for item in specialist_outputs),
                    summary=f"{specialist_name} 处理任务 {len(tasks)} 个",
                )
            ],
        }

    def _trace(
        self,
        *,
        node_name: str,
        started: float,
        input_count: int,
        output_count: int,
        summary: str,
    ) -> ExecutionTrace:
        """构造节点 trace。"""
        ended = time.perf_counter()
        now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return ExecutionTrace(
            trace_id=f"trace-{uuid4().hex[:8]}",
            node_name=node_name,
            status="completed",
            started_at=now_text,
            ended_at=now_text,
            elapsed_ms=int((ended - started) * 1000),
            summary=summary,
            input_count=input_count,
            output_count=output_count,
        )

    def _extract_definition_records(self, chunk_id: str, text: str) -> list[dict[str, str]]:
        """抽定义项。"""
        records: list[dict[str, str]] = []
        for index, match in enumerate(
            re.finditer(
                r"(?:“(?P<quoted>[^”]{2,24})”|(?P<plain>[\u4e00-\u9fa5A-Za-z]{2,24}))\s*(?:系指|是指|指)\s*(?P<desc>[^。；\n]{4,120})",
                text,
            ),
            start=1,
        ):
            term = (match.group("quoted") or match.group("plain") or "").strip()
            description = (match.group("desc") or "").strip()
            if term and description:
                records.append(
                    {
                        "definition_id": f"{chunk_id}-definition-{index}",
                        "term": term,
                        "description": description,
                    }
                )
        return records

    def _unique(self, items: list[str]) -> list[str]:
        """保持顺序去重。"""
        result: list[str] = []
        for item in items:
            value = str(item).strip()
            if value and value not in result:
                result.append(value)
        return result

    def _find_arbitration_duplicate(
        self,
        finding: MergedFinding,
        retained: list[MergedFinding],
    ) -> int | None:
        """查找可归并项。"""
        current_title = self._normalize_free_text(finding["title"])
        current_issue = self._normalize_free_text(finding["issue"])
        current_sources = set(finding["source_chunk_ids"])
        for index, item in enumerate(retained):
            title_similarity = self._similarity(current_title, self._normalize_free_text(item["title"]))
            issue_similarity = self._similarity(current_issue, self._normalize_free_text(item["issue"]))
            source_overlap = bool(current_sources.intersection(item["source_chunk_ids"]))
            if title_similarity >= 0.88 and (issue_similarity >= 0.72 or source_overlap):
                return index
        return None

    def _merge_findings(self, retained: MergedFinding, incoming: MergedFinding) -> MergedFinding:
        """合并 finding。"""
        return MergedFinding(
            finding_id=retained["finding_id"],
            title=retained["title"] if len(retained["title"]) <= len(incoming["title"]) else incoming["title"],
            issue=self._merge_texts([retained["issue"], incoming["issue"]]),
            suggestion=self._pick_better_text(retained["suggestion"], incoming["suggestion"]),
            evidence=self._merge_texts([retained["evidence"], incoming["evidence"]]),
            risk_level=self._pick_higher_risk(retained["risk_level"], incoming["risk_level"]),
            source_task_ids=self._unique([*retained["source_task_ids"], *incoming["source_task_ids"]]),
            source_chunk_ids=self._unique([*retained["source_chunk_ids"], *incoming["source_chunk_ids"]]),
            source_specialists=self._unique([*retained["source_specialists"], *incoming["source_specialists"]]),
            route_topics=self._unique([*retained["route_topics"], *incoming["route_topics"]]),
            rule_hits=[*retained["rule_hits"], *incoming["rule_hits"]],
        )

    def _merge_texts(self, texts: list[str]) -> str:
        """合并文本。"""
        merged: list[str] = []
        for text in texts:
            value = str(text).strip()
            normalized = self._normalize_free_text(value)
            if not value:
                continue
            if any(normalized and normalized in self._normalize_free_text(item) for item in merged):
                continue
            merged.append(value)
        return "；".join(merged)

    def _pick_better_text(self, left: str, right: str) -> str:
        """选择更完整的建议。"""
        return left if len(left.strip()) >= len(right.strip()) else right

    def _pick_higher_risk(self, left: str, right: str) -> str:
        """返回更高风险等级。"""
        order = {"低": 1, "中": 2, "高": 3}
        return left if order.get(left, 1) >= order.get(right, 1) else right

    def _normalize_free_text(self, text: str) -> str:
        """标准化自由文本。"""
        return re.sub(r"\s+", "", str(text).strip())

    def _similarity(self, left: str, right: str) -> float:
        """计算文本相似度。"""
        if not left or not right:
            return 0.0
        from difflib import SequenceMatcher

        return SequenceMatcher(None, left, right).ratio()

    def _specialist_node_name(self, specialist_name: str) -> str:
        """生成节点名称。"""
        mapping = {
            SPECIALIST_PAYMENT: "specialist_payment",
            SPECIALIST_LIABILITY: "specialist_liability",
            SPECIALIST_DISPUTE: "specialist_dispute",
            SPECIALIST_DEFINITION: "specialist_definition",
        }
        return mapping[specialist_name]

    def _normalize_risk_level(self, value: Any) -> str:
        """归一化风险等级。"""
        text = str(value or "").strip()
        if "高" in text:
            return "高"
        if "中" in text:
            return "中"
        if "低" in text:
            return "低"
        return "中"
