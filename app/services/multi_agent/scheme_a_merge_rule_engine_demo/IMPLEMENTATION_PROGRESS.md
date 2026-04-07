# 方案 A Demo 开发进度

更新时间：2026-04-07

## 1. 当前目标

- 基于 `DEVELOPMENT_PLAN.md` 落一个最小可运行骨架。
- 优先打通：
- 证据快照
- Planner 派单
- Specialist 并发审阅
- Findings 汇总
- Merge + Arbitration
- Rule Checker
- 结果落盘

## 2. 已完成

### 已完成代码文件

- `merge_rule_engine_demo.py`

### 已完成能力

- 已复用 `multi_agent` 目录下的 `config` 与 `review_toolkit` 基础能力。
- 已复用 `merge_arbitration_demo.py` 的冲突检测与仲裁主逻辑。
- 已实现最小 `EvidenceSnapshot / SpecialistTask / CheckedFinding / RuleHit` 数据结构。
- 已实现 Planner 基于分块内容派发 Specialist 任务。
- 已实现 Specialist 并发审阅。
- 已实现结构化 findings 汇总后进入 `Merge + Arbitration`。
- 已实现最小 Rule Checker。
- 已实现 `accepted / needs_recheck / suppressed` 三路输出。
- 已实现文本与 JSON 结果落盘。
- 已实现 fake model 自测入口。
- 已实现真实模型运行入口。

## 3. 当前最小规则

- 高风险无证据拦截。
- 占位文本拦截。
- 空建议拦截。
- 重复 finding 抑制。

## 4. 尚未完成

- 规则 DSL / YAML 规则包加载。
- 更完整的 `risk_score` 计算与排序。
- 更细的证据句柄校验。
- 更强的 Planner 路由策略。
- 更强的 Merge 去重与主题归并。
- 更完整的 `needs_recheck` 原因分类。
- 数据库真实落表。

## 5. 当前注意点

- 当前骨架仍偏“最小可运行”，不是最终版规则引擎。
- Specialist 审阅目前仍复用 `review_chunk` 主提示词能力，尚未改成专门的结构化 specialist prompt。
- Rule Checker 当前是内置规则，不具备热更新能力。
- `suppressed` 目前主要依赖简单重复判断，后续需要更细的语义归并。
- 当前数据库字段仅在结果 JSON 中保留，没有真实持久化。

## 6. 下一步建议

1. 先运行 fake model 自测，确保骨架稳定。
2. 再用真实合同跑一轮，观察：
- accepted 数量
- needs_recheck 数量
- 占位内容是否仍有泄漏
- 总耗时
3. 根据真实结果再决定先增强 Planner 还是先增强 Rule Checker。

## 7. 当前验证结果

- 已执行：`uv run python app/services/multi_agent/scheme_a_merge_rule_engine_demo/merge_rule_engine_demo.py`
- 本地 fake model 自测通过。
- 当前自测结果：
- `chunk_count = 3`
- `task_count = 6`
- `accepted_count = 3`
- `needs_recheck_count = 0`
- `suppressed_count = 2`
- 结果文本与 JSON 文件均成功落盘。

## 8. 当前边界说明

- 自测通过仅代表骨架链路可跑通，不代表规则效果已调优完成。
- 目前 `needs_recheck_count = 0`，说明当前规则强度仍偏保守，后续需要用真实合同继续校验。
