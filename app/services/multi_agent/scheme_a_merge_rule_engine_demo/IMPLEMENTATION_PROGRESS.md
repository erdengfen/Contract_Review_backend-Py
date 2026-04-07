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
- 已收紧 Planner 派单策略，避免默认每块扩成双 specialist。
- 已实现 Specialist 并发审阅。
- 已实现结构化 findings 汇总后进入 `Merge + Arbitration`。
- 已实现进入 checker 前的主题级预归并。
- 已实现最小 Rule Checker。
- 已实现 `accepted / needs_recheck / suppressed` 三路输出。
- 已实现文本与 JSON 结果落盘。
- 已实现 fake model 自测入口。
- 已实现真实模型运行入口。

## 3. 当前最小规则

- 高风险无证据拦截。
- 占位文本拦截。
- 空建议拦截。
- 标题近义归并抑制。
- 同证据重复抑制。
- 弱证据拦截。
- 空泛建议拦截。
- 总结性标题混入拦截。

## 4. 尚未完成

- 规则 DSL / YAML 规则包加载。
- 更完整的 `risk_score` 计算与排序。
- 更细的证据句柄校验。
- 更强的 Planner 路由策略。
- 更强的 Merge 去重与主题归并。
- 更完整的 `needs_recheck` 原因分类与分级阈值。
- 数据库真实落表。

## 5. 当前注意点

- 当前骨架仍偏“最小可运行”，不是最终版规则引擎。
- Specialist 审阅目前仍复用 `review_chunk` 主提示词能力，尚未改成专门的结构化 specialist prompt。
- Rule Checker 当前是内置规则，不具备热更新能力。
- `suppressed` 已引入标题近义与同证据重复抑制，但仍缺少更强的主题级聚合。
- 当前已有主题级预归并，部分重复问题会在进入 checker 前被吸收，因此 `suppressed` 可能回落为 0，这不一定代表去重失效，需要结合 `预归并收束数量` 一起判断。
- 当前数据库字段仅在结果 JSON 中保留，没有真实持久化。
- 当前耗时绝大部分仍集中在 Specialist 并发审阅，主瓶颈不在 Planner 或 Checker。

## 6. 下一步建议

1. 继续保留 fake model 自测，确保结构回归稳定。
2. 用真实合同持续观察：
- accepted 数量
- needs_recheck 数量
- suppressed 数量
- 占位内容是否仍有泄漏
- 弱证据与空泛建议是否被有效拦截
- 总耗时
3. 下一步优先压缩 Specialist 任务数，再决定是否继续增强 Merge 归并。
4. 继续观察 `未派发任务分块数 / 双 specialist 分块数 / 预归并收束数量` 三个指标，避免 Planner 收得过死导致漏审。

## 7. 当前验证结果

- 已执行：`uv run python app/services/multi_agent/scheme_a_merge_rule_engine_demo/merge_rule_engine_demo.py`
- 本地 fake model 自测通过。
- 当前自测结果：
- `chunk_count = 3`
- `task_count = 6`
- `accepted_count = 2`
- `needs_recheck_count = 1`
- `suppressed_count = 2`
- 结果文本与 JSON 文件均成功落盘。
- 已执行真实合同测试：
- `uv run python app/services/multi_agent/scheme_a_merge_rule_engine_demo/merge_rule_engine_demo.py --file "data/重庆第二师范学院南山校区学生宿舍三期建设工程EPC总承包合同2025.4.27最终版.docx"`
- 最新真实运行结果：
- 第一轮规则增强结果：
- `chunk_count = 35`
- `task_count = 70`
- `structured_pool_count = 361`
- `conflict_count = 50`
- `accepted_count = 109`
- `needs_recheck_count = 48`
- `suppressed_count = 32`
- `elapsed_seconds = 897.382`
- 阶段耗时：
- `parse_and_split = 0.255s`
- `build_snapshot = 0.027s`
- `planner_dispatch = 0.036s`
- `specialist_reviews = 892.046s`
- `merge_and_arbitration = 0.004s`
- `rule_checker = 5.014s`
- 第二轮 Planner 收紧 + 预归并结果：
- `chunk_count = 35`
- `task_count = 40`
- `zero_task_chunk_count = 0`
- `multi_specialist_chunk_count = 5`
- `structured_pool_count = 213`
- `conflict_count = 23`
- `precheck_merge_count = 25`
- `accepted_count = 89`
- `needs_recheck_count = 19`
- `suppressed_count = 0`
- `elapsed_seconds = 542.283`
- 阶段耗时：
- `parse_and_split = 0.271s`
- `build_snapshot = 0.029s`
- `planner_dispatch = 0.055s`
- `specialist_reviews = 538.944s`
- `merge_and_arbitration = 0.002s`
- `precheck_consolidation = 0.913s`
- `rule_checker = 2.068s`
- 当前观察结论：
- `task_count` 已从 `70` 降到 `40`
- `specialist_reviews` 耗时已从约 `892s` 降到约 `539s`
- `suppressed_count` 回落到 `0`，但新增了 `precheck_merge_count = 25`，说明重复问题前移到了 checker 之前收束
- `needs_recheck_count` 从 `48` 降到 `19`，说明收束后进入规则校验的问题池更集中，但仍需继续确认是否存在漏拦截

## 8. 当前边界说明

- 自测通过仅代表骨架链路可跑通，不代表规则效果已调优完成。
- 当前真实结果显示规则增强已生效，但主要瓶颈仍是 `specialist_reviews` 阶段的模型调用耗时。
- 当前 `suppressed_count = 32`，说明重复抑制开始起作用，但主题级归并仍不够强。
- 当前 `needs_recheck_count = 48`，已不再只依赖占位文本规则，但仍需继续扩展证据质量和建议质量判定。
- 最新一轮中，主题级预归并已提前吸收了 25 条相近问题，说明“重复抑制从 checker 后移到 checker 前”已经生效。
- 但 `needs_recheck_count` 明显下降，也意味着下一步需要继续核查是否因为前置收束过强而压掉了部分应复核问题。
