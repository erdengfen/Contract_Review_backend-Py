# 方案 B Demo 开发进度

更新时间：2026-04-07

## 1. 当前目标

- 按 `DEVELOPMENT_PLAN.md` 开始实现方案 B 的 Phase B1。
- 直接使用 LangGraph 建立最小图骨架。
- 先打通：
- `parse_document`
- `split_and_index`
- `router`
- `specialist_*`
- `merge_evidence`
- `rule_gate_1`
- `arbitration`
- `rule_gate_2`
- `record_disputed_findings`
- `reporter`

## 2. 已确认口径

- `disputed_findings` 只保留一个结果区，使用 `gate_name` 区分来源。
- `gate_rules.py` 在方案 B 中独立维护，不直接复用方案 A 的 checker 文件。
- `disputed_findings` 在文本报告中默认展示摘要和规则命中，不展示全文。
- 数据库设计仅保留字段，不做真实数据库实现。
- RAG 仅保留字段，不做真实检索接入。

## 3. 本轮计划

- 检查并补充 `langgraph` 依赖。
- 创建方案 B 的最小目录与基础文件。
- 实现最小 `GraphState` 和 LangGraph 主图。
- 先用假模型或最小结构验证跑通节点链路。

## 4. 尚未完成

- 真实合同运行验证。
- 节点耗时和更细的阶段统计。
- 更强的 arbitration 与 Gate-2 规则。
- 结果文本的进一步收束与摘要优化。

## 5. 当前注意点

- 方案 B 必须直接使用 LangGraph，不再走函数模拟图。
- 本阶段重点是图编排闭环，不是立即追求规则复杂度。
- 如果环境里没有 `langgraph`，需要先补依赖并更新锁文件。

## 6. 本轮已完成

- 已通过 `uv add langgraph` 补充方案 B 所需依赖，并更新 `pyproject.toml` 与 `uv.lock`。
- 已新增最小骨架文件：
- `graph_demo.py`
- `graph_state.py`
- `node_handlers.py`
- `router_rules.py`
- `gate_rules.py`
- 已实现最小 LangGraph 主图，节点包括：
- `parse_document`
- `split_and_index`
- `router`
- `specialist_payment`
- `specialist_liability`
- `specialist_dispute`
- `specialist_definition`
- `merge_evidence`
- `rule_gate_1`
- `arbitration`
- `rule_gate_2`
- `record_disputed_findings`
- `reporter`
- 已实现独立于方案 A 的 Gate 规则文件。
- 已实现文本与 JSON 结果落盘。
- 已实现方案 B 的本地假模型自测入口。

## 7. 当前验证结果

- 已执行：
- `uv run python app/services/multi_agent/scheme_b_langgraph_workflow_demo/graph_demo.py`
- 自测通过。
- 当前自测结果：
- `chunk_count = 3`
- `router_task_count = 3`
- `accepted_count = 2`
- `disputed_count = 1`
- `trace_count = 13`
- 文本与 JSON 结果均成功落盘。

## 8. 下一步建议

1. 用真实合同跑一轮方案 B，先看 LangGraph 节点 trace 和结果结构是否稳定。
2. 再补节点耗时统计，特别是 specialist 节点和 Gate 节点耗时。
3. 然后再决定是否优先增强 Router，还是先增强 Gate-2 与 arbitration。

## 9. 真实合同运行结果

- 已执行：
- `uv run python app/services/multi_agent/scheme_b_langgraph_workflow_demo/graph_demo.py --file "data/重庆第二师范学院南山校区学生宿舍三期建设工程EPC总承包合同2025.4.27最终版.docx"`
- 运行成功，结果已落盘：
- `app/services/multi_agent/result/scheme_b_langgraph_重庆第二师范学院南山校区学生宿舍三期建设工程EPC总承包合同2025.4.27最终版_20260407_143442.txt`
- `app/services/multi_agent/result/scheme_b_langgraph_重庆第二师范学院南山校区学生宿舍三期建设工程EPC总承包合同2025.4.27最终版_20260407_143442.json`

- 关键统计：
- `chunk_count = 35`
- `router_task_count = 35`
- `specialist_output_count = 124`
- `merged_finding_count = 648`
- `accepted_count = 332`
- `disputed_count = 117`
- `suppressed_count = 133`
- `elapsed_seconds = 552.856`

- 当前观察：
- Router 目前偏宽，35 个 chunk 触发了 124 个 specialist 输出。
- 当前 Gate-1 主要拦截占位内容，`GATE1-PLACEHOLDER-001 = 60`。
- 当前 Gate-2 主要拦截总结性标题，`GATE2-SUMMARY-TITLE-001 = 48`。
- arbitration 已开始工作，但 `accepted_count = 332` 仍偏高，说明主题级收束明显不够。
- 结果文本已包含 `specialist_distribution / gate_distribution / rule_distribution / disputed 摘要 / execution_trace`。
