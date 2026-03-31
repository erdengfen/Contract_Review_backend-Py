# RAG Vibe Coding Plan

## Goal
- 在合同审阅 `review_contract` 调用模型前，先对当前 chunk 执行 RAG 检索。
- 召回结果必须同时包含“外部法律依据”和“内部审阅规则”。
- RAG 结果要被安全、可追溯地拼入 prompt，以提升审阅准确度。

## Document Maintenance Rule
- 每次在 `app/rag/` 下新增或修改代码后，必须同步更新本文件。
- 本文件必须持续维护“已完成”“未完成”“下一步”三部分。
- 若实现顺序偏离计划，必须记录原因，避免后续 agent 误判状态。

## Current Progress

### 已完成
- 已创建 `app/rag/` 包和 `clients/` 子包初始化文件。
- 已创建 `app/rag/config.py`，完成 RAG 配置骨架。
- 已创建 `app/rag/schemas.py`，完成基础 schema 骨架。
- 已创建 `app/rag/clients/qdrant_client.py`，完成 Qdrant 客户端骨架。
- 已创建 `app/rag/clients/embedding_local.py`，完成本地 embedding 客户端骨架。
- 已创建 `app/rag/clients/embedding_remote.py`，完成远程 embedding 客户端骨架。
- 已完成本轮新增文件的中文化注释、docstring 和字段描述整理。
- 已完成最小语法检查与导入验证。

### 未完成
- 尚未把 `app/rag/config.py` 接入现有主配置系统。
- 尚未安装和接入 `qdrant-client`。
- 尚未实现本地 embedding 后端。
- 尚未实现远程 embedding provider 的业务接线。
- 尚未实现 retriever、多路 query、融合、rerank、context builder。
- 尚未接入 `app/services/contract_review.py`。

## Constraints
- Qdrant 必须独立容器部署。
- collection 必须拆分为：
- `external_legal_kb`
- `internal_review_rules`
- 本地模型推理仅允许轻量 embedding 模型。
- 必须同时支持本地与在线两种 embedding provider。
- provider 切换必须通过配置完成。
- 首轮召回必须使用混合检索和多路召回。

## Phase 0: Skeleton
- 新建目录：
- `app/rag/config.py`
- `app/rag/schemas.py`
- `app/rag/clients/qdrant_client.py`
- `app/rag/clients/embedding_local.py`
- `app/rag/clients/embedding_remote.py`
- `app/rag/retrievers/hybrid_fusion.py`
- `app/rag/retrievers/multi_query.py`
- `app/rag/retrievers/external_legal_retriever.py`
- `app/rag/retrievers/internal_rules_retriever.py`
- `app/rag/retrievers/reranker.py`
- `app/rag/services/rag_service.py`
- `app/rag/services/context_builder.py`
- `app/rag/ingest/chunkers.py`
- `app/rag/ingest/external_legal_ingest.py`
- `app/rag/ingest/internal_rules_ingest.py`
- 所有模块先建立最小可导入骨架，不急着一次写满。

## Phase 1: Config First
- 在 `app/rag/config.py` 定义统一 RAG 配置模型。
- 配置至少覆盖：
- `enabled`
- `embedding.provider_mode = local | remote`
- `embedding.local_model_name`
- `embedding.remote_provider`
- `embedding.remote_model`
- `embedding.remote_base_url`
- `embedding.remote_api_key`
- `qdrant.host`
- `qdrant.port`
- `qdrant.external_collection`
- `qdrant.internal_collection`
- `retrieval.enable_dense`
- `retrieval.enable_sparse`
- `retrieval.enable_multi_query`
- `retrieval.top_k`
- `filters.default_region`
- `filters.default_industry`
- 配置必须能挂到主 `settings`，但不要在首轮改太多无关主配置代码。

## Phase 2: Schema And Metadata
- 为两个 collection 设计严格 payload schema。
- `external_legal_kb` 必须包含：
- `doc_id`
- `source_type`
- `source_level`
- `title`
- `article_no`
- `content`
- `region`
- `industry`
- `effective_status`
- `contract_type_tags`
- `risk_tags`
- `internal_review_rules` 必须包含：
- `rule_id`
- `rule_type`
- `title`
- `content`
- `organization_scope`
- `contract_type_tags`
- `risk_tags`
- `priority`
- `enabled`
- 在 `schemas.py` 中定义统一的数据结构和返回对象。

## Phase 3: Qdrant Client
- 在 `clients/qdrant_client.py` 封装 Qdrant 连接。
- 连接配置必须只从 `app/rag/config.py` 读取。
- 需要提供：
- 创建 collection
- upsert points
- dense 查询
- sparse 查询
- hybrid query
- payload filter query
- 不要在业务代码里直接 new Qdrant client。

## Phase 4: Embedding Providers
- 在 `embedding_local.py` 实现本地轻量 embedding provider。
- 默认模型建议使用：`BAAI/bge-small-zh-v1.5`
- 本地实现必须可 CPU 跑通。
- 在 `embedding_remote.py` 实现在线 embedding provider。
- 在线 provider 必须兼容 OpenAI-style embedding API。
- 两者对外暴露统一接口：
- `embed_documents(texts)`
- `embed_query(text)`
- provider 切换由配置决定，不允许调用方分支硬编码。

## Phase 5: Ingestion
- 先分别实现两套入库链路，不要混写。
- `external_legal_ingest.py`
- 输入：法律、司法解释、行业监管规范、地方法规
- 切分优先按法条结构，不要先按固定 token 粗切
- 入库前必须补齐效力状态、地区、行业等元数据
- `internal_rules_ingest.py`
- 输入：内部审阅规则、风险规则、标签规则、审阅口径
- 必须补齐适用范围、优先级、启用状态
- 首版可以先支持 JSONL / YAML / CSV 之一，但要固定格式。

## Phase 6: Retrieval
- 实现多路 query 生成，不要只有原始 chunk 一路。
- 最少三类 query：
- 原始 chunk query
- 法律问题 query
- 风险标签 query
- 对每类 query，在两个 collection 上并行执行：
- dense 检索
- sparse 检索
- 每个 collection 内部先做 hybrid 融合。
- 再在应用层做跨 query、跨 collection 的加权 RRF。

## Phase 7: Rerank
- 首版 rerank 默认使用在线 provider。
- 只对候选集 rerank，禁止全库 rerank。
- 建议先输出：
- 外部法律 top 6
- 内部规则 top 4
- rerank 模型切换和开关也必须走配置。

## Phase 8: Context Builder
- 在 `context_builder.py` 中把召回结果转为受控 prompt 文本。
- 输出必须分两段：
- `## 外部法律依据`
- `## 内部审阅规则`
- 每条结果必须保留来源标题和条号/规则编号。
- 必须有长度预算控制。
- 召回为空时必须返回空上下文，而不是抛异常。

## Phase 9: Integrate Into review_contract
- 在 `app/services/contract_review.py` 中接入 `rag_service`。
- 推荐方式：
- `ContractReviewService.__init__(..., rag_service=None)`
- `review_contract` 内部在构造最终 prompt 前调用：
- `rag_service.retrieve_for_review(...)`
- 返回 `prompt_context`
- 将 `prompt_context` 作为新段落拼入审阅 prompt。
- RAG 失败时必须降级，不得阻断原审阅流程。

## Phase 10: Validation
- 最低验证要求：
- 两个 collection 可独立检索
- dense / sparse 都可用
- 多路召回可融合
- 地区过滤生效
- 行业过滤生效
- 失效法规被过滤
- 禁用内部规则不参与召回
- RAG 失败时 review_contract 仍可运行
- prompt 中可见外部法律与内部规则分段

## Suggested Build Order
1. `config.py`
2. `schemas.py`
3. `clients/qdrant_client.py`
4. `clients/embedding_local.py`
5. `clients/embedding_remote.py`
6. `ingest/chunkers.py`
7. `ingest/external_legal_ingest.py`
8. `ingest/internal_rules_ingest.py`
9. `retrievers/multi_query.py`
10. `retrievers/hybrid_fusion.py`
11. `retrievers/external_legal_retriever.py`
12. `retrievers/internal_rules_retriever.py`
13. `retrievers/reranker.py`
14. `services/context_builder.py`
15. `services/rag_service.py`
16. 接入 `app/services/contract_review.py`

## Next Step
1. `app/rag/retrievers/multi_query.py`
2. `app/rag/retrievers/hybrid_fusion.py`
3. `app/rag/retrievers/external_legal_retriever.py`
4. `app/rag/retrievers/internal_rules_retriever.py`
5. `app/rag/retrievers/reranker.py`

## Non-Goals For First Iteration
- 不要第一版就做复杂评测平台。
- 不要第一版就引入本地重型 reranker。
- 不要第一版就把所有法规源一次性全量灌入。
- 不要先改动 router / API / 返回 schema。

## Done Criteria
- RAG 配置可切换本地 / 在线 embedding。
- Qdrant 独立容器接入完成。
- 两个 collection 均可入库和检索。
- 审阅前可稳定召回并注入外部法律依据和内部规则。
- 失败时有降级路径。
- 所有新增逻辑不破坏现有审阅主链路。
