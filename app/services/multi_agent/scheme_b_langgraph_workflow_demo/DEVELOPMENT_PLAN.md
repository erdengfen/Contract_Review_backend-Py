# 方案 B Demo 开发文档

## 1. 定位

- 方案来源：`MULTI_AGENT_LEGAL_REVIEW_RULE_ENGINE_PLAN.md` 中的方式 B。
- 目标：设计一个基于 LangGraph 思维方式的图式工作流 demo，用节点化方式表达合同审阅多 agent 链路。
- 当前阶段定位：仅做 demo 试运行文档设计，不实现完整 LangGraph 生产图，不接真实数据库，只预留关键字段。

一句话概括：

`图式工作流编排 -> Router 主题路由 -> Specialist 节点并行 -> 证据归并 -> Rule Gate -> Arbitration -> Gate-2 -> Accepted / Needs Recheck`

---

## 2. 架构链路

## 2.1 Graph 节点链路

建议节点顺序：

1. `parse_document`
2. `split_and_index`
3. `build_snapshot`
4. `router`
5. `specialist_payment`
6. `specialist_liability`
7. `specialist_dispute`
8. `specialist_definition`
9. `merge_evidence`
10. `rule_gate_1`
11. `arbitration`
12. `rule_gate_2`
13. `reporter`

## 2.2 路由逻辑

- `router` 不直接做最终判断。
- 只负责按条款主题或规则标签，将 chunk 发送到一个或多个 specialist 节点。
- 节点输出统一写入图状态，不允许自由文本乱写共享状态。

## 2.3 双 Gate 设计

### Gate-1

- 检查完整性、占位词、证据字段是否齐全。
- 不合格直接打入 `needs_recheck_pool`。

### Gate-2

- 在仲裁后执行一致性、冲突收束、质量规则。
- 只允许最终可展示结果进入 `accepted_findings`。

---

## 3. demo 范围

### 3.1 本阶段要做

- 设计图式状态对象。
- 明确节点输入输出。
- 明确路由规则和分支收束点。
- 预留 LangGraph 对接接口，但本阶段不要求真实接 LangGraph 运行。

### 3.2 本阶段不做

- 不做完整状态持久化。
- 不做复杂人工复核界面。
- 不做真正的数据库事务回放。
- 不做完整规则 DSL 管理后台。

---

## 4. 目录建议

```text
app/services/multi_agent/scheme_b_langgraph_workflow_demo/
  DEVELOPMENT_PLAN.md
  graph_demo.py
  graph_state.py
  node_handlers.py
  router_rules.py
```

说明：

- `graph_demo.py`：主入口。
- `graph_state.py`：图状态定义。
- `node_handlers.py`：节点处理逻辑。
- `router_rules.py`：主题路由和节点选择规则。

---

## 5. 图状态设计

## 5.1 GraphState

关键字段建议：

- `run_id`
- `snapshot_id`
- `file_path`
- `file_type`
- `chunks`
- `chunk_index_map`
- `router_tasks`
- `specialist_outputs`
- `merged_findings`
- `accepted_findings`
- `needs_recheck_findings`
- `suppressed_findings`
- `execution_trace`
- `elapsed_seconds`

## 5.2 RouterTask

- `task_id`
- `chunk_id`
- `route_topics`
- `target_specialists`
- `priority`
- `context_handles`

## 5.3 SpecialistOutput

- `task_id`
- `specialist_name`
- `findings`
- `raw_output`
- `status`

## 5.4 ExecutionTrace

- `trace_id`
- `node_name`
- `status`
- `started_at`
- `ended_at`
- `elapsed_ms`
- `summary`

---

## 6. 节点职责定义

## 6.1 parse_document

- 解析合同文件。
- 输出基础文本。

## 6.2 split_and_index

- 按现有 toolkit 分块。
- 同时生成稳定 `chunk_id` 和简单主题标签。

## 6.3 build_snapshot

- 构建共享证据快照。
- 抽定义项、引用标记、附件标识。

## 6.4 router

- 基于关键词、条款模式和定义命中进行主题路由。
- 为后续 specialist 构造 `RouterTask`。

## 6.5 specialist 节点

- 每个 specialist 只处理自己主题。
- 只输出结构化 findings。

## 6.6 merge_evidence

- 合并多个 specialist 输出。
- 保留来源节点、来源 task、证据锚点。

## 6.7 rule_gate_1

- 拦截空证据、高风险弱结论、占位文本。

## 6.8 arbitration

- 处理冲突、重复、跨块联动。
- 输出全局统一口径。

## 6.9 rule_gate_2

- 检查最终质量、一致性和可展示性。

## 6.10 reporter

- 输出文本结果、JSON 结果、运行轨迹摘要。

---

## 7. 最小规则与路由策略

## 7.1 首批 router 策略

- 命中 `付款/预付款/进度款/结算/验收` -> 付款 specialist
- 命中 `违约/赔偿/免责/责任/索赔` -> 责任 specialist
- 命中 `争议/仲裁/法院/通知/解除/终止` -> 争议 specialist
- 命中 `定义/系指/附件/附表/空白/留空` -> 定义 specialist

## 7.2 首批 rule gate 规则

- 高风险无证据 -> `needs_recheck`
- 占位输出 -> `needs_recheck`
- 仲裁后重复 finding -> `suppressed`
- 依赖句柄无法解析 -> `needs_recheck`

---

## 8. 数据库与表结构预留

当前不做真实建表，只预留字段。

## 8.1 workflow_run（预留）

- `id`
- `run_id`
- `graph_version`
- `rule_version`
- `model_name`
- `snapshot_id`
- `status`
- `elapsed_seconds`
- `created_at`

## 8.2 workflow_node_trace（预留）

- `id`
- `run_id`
- `node_name`
- `status`
- `started_at`
- `ended_at`
- `elapsed_ms`
- `summary`

## 8.3 workflow_finding（预留）

- `id`
- `run_id`
- `finding_id`
- `checker_status`
- `risk_level`
- `source_node`
- `source_task_id`
- `snapshot_id`
- `created_at`

## 8.4 workflow_rule_hit（预留）

- `id`
- `finding_id`
- `rule_id`
- `gate_name`
- `result`
- `message`
- `created_at`

说明：

- 这些字段优先服务图执行回放和审计。
- demo 阶段可仅在 JSON 结果中体现。

---

## 9. 开发步骤

### Phase B1

- 先实现纯 Python 图状态流转，不强依赖 LangGraph 包。
- 用函数节点模拟 Graph 思维。

### Phase B2

- 抽出 `GraphState` 与 `ExecutionTrace`。
- 让每个节点都写入 trace。

### Phase B3

- 实现最小 Router + 4 个 specialist 节点。
- 接入双 Gate。

### Phase B4

- 增加结果报告与真实合同回归运行。
- 若后续决定继续，可再切换为真实 LangGraph 编排。

---

## 10. 验证要求

### 10.1 本地结构验证

- 假模型下所有节点能完整走通。
- `execution_trace` 中能看到每个节点的开始、结束和状态。

### 10.2 真实运行验证

- 真实合同下能输出：
- `accepted_findings`
- `needs_recheck_findings`
- 节点执行轨迹
- 总耗时

---

## 11. 风险点

- 若一开始就强依赖 LangGraph 真实实现，工程复杂度会偏高。
- Graph 节点过细会增加理解成本和调试成本。
- 若 Router 粒度过粗，会导致 specialist 分发失衡；过细则会导致任务爆炸。

---

## 12. 当前阶段结论

- 方案 B 更适合作为中长期主线，而不是当前最先落地的默认 demo。
- 它最大的价值不是立即提升结论质量，而是提供更强的编排透明度、节点追踪能力和未来 HITL 接入口。
- 当前 demo 阶段建议先按“函数节点模拟图工作流”的方式落地，不急于一次性写成完整 LangGraph 生产图。
