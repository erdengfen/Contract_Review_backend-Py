# PLANS.md

本文档用于记录合同审阅后端的架构重构计划、开发进度、阶段验收和风险状态。后续涉及分步开发或长期重构任务时，必须同步更新本文档。

## 重构定位

- 本轮重构重点是 agent 能力逻辑，不优先改动现有后端业务接口。
- 当前已存在的 FastAPI 接口入参字段、出参字段、SSE 事件结构全部冻结，禁止在重构中修改。
- 后端逻辑与 agent 能力逻辑需要逐步解耦：后端负责接口、鉴权、任务、会话、落库和状态；agent 负责文档感知、解析、分块、RAG、skills、多 agent 编排、LLM 调用和结构化输出。
- `src/backend/` + `src/agent/` 作为目标架构方向可行，但不做一次性大搬迁；优先通过契约层和适配层迁移主审阅链路。
- `app/services/multi_agent/` 当前仍按实验区看待，不能直接作为生产入口接入。

## 当前对外接口基线

当前合同审阅能力对外主要暴露在 `app/router/review_task.py`，并由 `main_new.py` 注册到 `/api/review_task`。

| 接口 | 文件 | 当前职责 | 重构要求 |
| --- | --- | --- | --- |
| `POST /api/review_task/start_task` | `app/router/review_task.py` | 启动审阅任务，SSE 输出风险点和总结 | 路径、入参字段、SSE 字段保持不变，内部可切换到新 agent 编排 |
| `POST /api/review_task/accept_risk_point` | `app/router/review_task.py` | 接受或取消接受风险点修订 | 保持后端结果处理接口，不下沉到 agent |
| `POST /api/review_task/accept_contract_file` | `app/router/review_task.py` | 修改合同文件整体修订状态 | 保持后端结果处理接口，不下沉到 agent |

相关但不属于主审阅 agent 入口的接口：

| 接口 | 文件 | 关系 |
| --- | --- | --- |
| `POST /api/chat/chat` | `app/router/chat.py` | 合同聊天 LLM 流式能力，可后续复用 agent 的模型网关 |
| `POST /api/contract/upload` | `app/router/contract.py` | 文件上传、解析和合同信息抽取，后续应拆出文档感知层 |
| `POST /api/session/session_history_detail` | `app/router/session.py` | 读取审阅历史，字段必须保持兼容 |
| `POST /api/comparison_task/start` | `app/router/comparison_task.py` | 合同比对能力，当前不是 agent 审阅链路 |

## 目标职责边界

### backend 负责

- FastAPI 路由、鉴权、中间件、请求响应模型和接口兼容。
- 用户、会话、文件、审阅任务、审阅结果、比对结果等数据库读写。
- 任务状态流转、SSE 包装、接口错误码和现有前端兼容。
- 文件元数据、上传下载入口、权限校验和审阅结果持久化。

### agent 负责

- 文件存储前后的安全清洗、提示词注入防护和文档格式统一。
- DOC、DOCX、PDF、扫描件 PDF、普通 PDF 的解析路由。
- 图片、表格、页码、版面序号、源文本定位和纯文本映射。
- 语义分块、硬切块修复、分块定位标记和后续修改定位参数。
- RAG 检索、知识库版本返回、模型切换、重向量化和 Langfuse 链路追踪。
- skills 调用、冲突处理、多 agent 异步审阅、合并和仲裁。
- LLM 输出解析、失败兜底和结构化审阅结果。

### 依赖规则

- `backend` 可以调用 `agent` 暴露的契约和编排入口。
- `agent` 不允许反向依赖 FastAPI 路由、SQLAlchemy 模型、CRUD、鉴权或中间件。
- `agent` 返回结构化结果，由 `backend` 负责转换成现有 SSE 和数据库记录。
- 共享配置、错误类型、日志结构可以放到 `shared`，但不得让 `shared` 变成业务逻辑堆放区。

## 目标目录草案

目标结构如下，实际迁移需分阶段推进：

```text
src/
  backend/
    main.py
    api/
      routers/
      schemas/
      dependencies/
      middleware/
    application/
      review_task_service.py
      chat_service.py
      file_service.py
      session_service.py
    infrastructure/
      db/
      redis/
      storage/
      repositories/

  agent/
    contracts/
      review_request.py
      review_result.py
      document_block.py
    document_intake/
      storage_guard.py
      format_normalizer.py
      pdf_classifier.py
      layout_mapping.py
      parsers/
    chunking/
      semantic_chunker.py
      chunk_repair.py
    review/
      orchestrator.py
      specialist_agents.py
      merger.py
      output_parser.py
    rag/
      retriever.py
      knowledge_version.py
      revectorize.py
    skills/
      conflict_resolution.py
      review_rules.py
    tracing/
      langfuse_tracer.py
    llm/
      model_gateway.py
      model_registry.py

  shared/
    config/
    logging/
    errors.py
```

迁移期间可以保留现有 `app/` 入口和接口路径。只有在接口基线、测试和适配层稳定后，再评估是否整体切换到 `src/` 布局。

## 会议记录转化为建设项

| 方向 | 记录内容 | 重构落点 | 状态 |
| --- | --- | --- | --- |
| 文件存储 | 存储阶段防提示词注入 | `agent/document_intake/storage_guard.py` | 未开始 |
| 文件存储 | 不同类型 DOC、DOCX 统一输出为 DOCX | `agent/document_intake/format_normalizer.py` | 未开始 |
| 文档解析 | 当前 DOC、DOCX 解析精度差，需验证 `python-docx` 等方案 | `agent/document_intake/parsers/` | 未开始 |
| 文档解析 | 不同 PDF 做物理判断，扫描件和普通 PDF 分流 | `agent/document_intake/pdf_classifier.py` | 未开始 |
| 文档解析 | 核实 DeepSeek OCR 对复杂表格的识别精度，评估是否需要 AI 补全 | 解析评测记录和 OCR fallback | 未开始 |
| 文档解析 | 非扫描件使用 MinerU + OCR + 文字处理进行解析 | PDF 解析路由 | 未开始 |
| 文档感知 | PDF 中图片、表格清洗为纯文本，并记录页标定位和源文本映射 | `agent/document_intake/layout_mapping.py` | 未开始 |
| 失败回退 | 解析失败、空文本、低置信度、外部服务失败时要有降级路径 | 解析路由 fallback 策略 | 未开始 |
| 文本分块 | 使用轻量模型保证分块语义完整 | `agent/chunking/semantic_chunker.py` | 未开始 |
| 文本分块 | 使用 AI 修复硬语义切块造成的语义损失 | `agent/chunking/chunk_repair.py` | 未开始 |
| 文本分块 | 切块时记录标注版面序号，供后续修改工具定位 | `DocumentBlock` 契约 | 未开始 |
| 审阅过程 | 调用 skills 分析，设计多 agent 范式 | `agent/review/orchestrator.py` | 未开始 |
| 审阅过程 | 多 agent 分别异步审阅，再合并仲裁 | `specialist_agents.py`、`merger.py` | 未开始 |
| RAG | 返回条文时同时返回 RAG 系统版本和知识库版本 | `agent/rag/knowledge_version.py` | 未开始 |
| RAG | 使用 Langfuse 做链路追踪 | `agent/tracing/langfuse_tracer.py` | 未开始 |
| RAG | 支持模型切换和重向量化 | `agent/llm/model_gateway.py`、`agent/rag/revectorize.py` | 未开始 |
| RAG | 自动更新和人工更新并存，先例反哺后需人工确认再更新 | RAG 更新流程设计 | 未开始 |
| skills | 增加冲突处理 skills | `agent/skills/conflict_resolution.py` | 未开始 |
| MCP 取舍 | MCP 必须调用会占用上下文空间，主审阅链路不应强依赖 MCP | agent 工具调用策略 | 未开始 |

## 重构分步计划

### Step 0：重构计划改版

- √ 将原泛化计划改为后端和 agent 解耦重构计划。
- √ 在 `PLANS.md` 中记录当前对外审阅接口基线。
- √ 将会议记录转化为文件存储、文档解析、分块、RAG、skills、多 agent 编排等建设项。
- √ 执行文档结构检查和 diff 检查。

### Step 1：接口基线冻结

- 【】固化当前审阅接口、聊天接口、上传接口、历史接口的路径和字段。
- 【】整理 `/api/review_task/start_task` 的 SSE 事件样例，包括 `message`、`end`、`error`。
- 【】生成或记录当前 OpenAPI 快照，作为后续重构兼容性对比基线。
- 【】明确哪些接口属于 agent 能力入口，哪些接口只属于后端结果处理。
- 【】完成只读检查和人工确认，不修改业务代码。

### Step 2：agent 契约层设计

- 【】定义 `ReviewRequest`，承载审阅所需的合同文本、合同类型、审查立场、审查尺度、上下文和追踪信息。
- 【】定义 `ReviewResult`，承载风险点、风险等级、风险分析、建议修改内容、证据和失败兜底信息。
- 【】定义 `DocumentBlock`，承载分块文本、页码、版面序号、源文本定位和后续修改定位参数。
- 【】定义 `KnowledgeHit`，承载 RAG 命中条文、来源、知识库版本和可追溯标识。
- 【】补充契约层结构测试，不接真实模型和外部服务。

### Step 3：文档感知与存储安全

- 【】设计存储阶段提示词注入防护规则，避免合同正文影响系统 prompt 和工具调用。
- 【】设计 DOC、DOCX 统一输出为 DOCX 的格式归一流程。
- 【】设计 PDF 物理类型判断逻辑，将扫描件 PDF 和普通 PDF 分流。
- 【】设计文件感知层输出结构，保留文件类型、页码、版面序号和解析置信度。
- 【】使用样例文件做结构验证，确认不改变上传接口返回字段。

### Step 4：解析与失败回退链路

- 【】验证当前 DOC、DOCX 解析精度，并评估 `python-docx` 等替换方案。
- 【】验证普通 PDF 使用 MinerU + OCR + 文字处理的解析效果。
- 【】验证 DeepSeek OCR 对复杂表格的识别精度，判断是否需要 AI 补全。
- 【】将图片、表格等版面元素清洗为纯文本，并记录映射回源文档的位置。
- 【】设计空文本、低置信度、解析异常、外部服务不可用时的失败回退策略。
- 【】形成解析评测记录和 fallback 策略说明。

### Step 5：语义分块与定位

- 【】设计替代纯长度切块的语义分块流程。
- 【】评估轻量模型用于保证分块语义完整的成本、速度和稳定性。
- 【】设计 AI 修复硬语义切块造成语义损失的流程。
- 【】在切块结果中保留页码、版面序号、源文本定位和修改定位参数。
- 【】补充分块完整性和定位结构测试。

### Step 6：RAG、模型网关与链路追踪

- 【】设计 RAG 返回结构，除条文外必须返回 RAG 系统版本和知识库版本。
- 【】设计模型网关，支持审阅模型、聊天模型、轻量分块模型和 embedding 模型切换。
- 【】设计重向量化流程，支持模型切换后的知识库重建。
- 【】设计 Langfuse trace 事件，覆盖文档感知、解析、分块、RAG、skills、agent 审阅、合并仲裁。
- 【】设计自动更新和人工更新并存的 RAG 更新流程，先例反哺必须经人工确认。
- 【】完成不依赖自然语言措辞的结构验证。

### Step 7：skills 与多 agent 编排

- 【】确定多 agent 设计范式，优先考虑异步 specialist 审阅后合并仲裁。
- 【】设计 specialist agent 的输入、输出、停止条件和失败兜底。
- 【】设计冲突处理 skills，用于处理多个 agent 审阅意见不一致的情况。
- 【】设计 RAG、skills 和审阅 agent 的上下文传递边界，避免上下文无限膨胀。
- 【】明确 MCP 不作为主审阅链路强依赖时的工具调用策略。
- 【】使用假模型跑通完整结构链路。

### Step 8：后端适配层接入

- 【】设计 backend 到 agent 的适配层，将现有 `ReviewTaskCreateRequest` 转换为 agent 契约。
- 【】将 agent 输出转换成现有 `ReviewTaskSSEResponse` 和审阅结果落库字段。
- 【】保持 `/api/review_task/start_task` 路径、入参字段、SSE 字段和事件顺序不变。
- 【】保持审阅任务状态流转、并发控制和结果落库顺序兼容。
- 【】完成 SSE 字段回归、落库顺序检查和最小链路验证。

### Step 9：旧链路收敛与文档对齐

- 【】清理或明确标记 `app/services/multi_agent/` 中仍属于 demo 的实现。
- 【】梳理旧 `ContractReviewService` 中 prompt 拼装、RAG、解析和 LLM 调用的迁移状态。
- 【】更新过期项目结构、启动方式、依赖入口和开发流程说明。
- 【】形成保留、迁移、废弃清单。
- 【】执行 `uv run pytest` 或与本阶段直接相关的最小测试。

## 迁移策略

- 第一阶段只建立契约和只读基线，不改现有接口和业务表结构。
- 第二阶段先在新 agent 模块中做可运行的最小链路，用假模型和样例文本验证结构。
- 第三阶段通过适配层把新 agent 输出转换成现有 `ReviewTaskSSEResponse` 和审阅结果落库字段。
- 第四阶段逐步把 `ContractReviewService` 中的 prompt 拼装、RAG、解析和 LLM 调用迁移到 agent 内部模块。
- 第五阶段再评估是否将 `main_new.py`、`app/router/`、`app/schemas/` 迁移到 `src/backend/`。

## 不在本轮优先处理

- 不优先修改用户、鉴权、中间件、数据库结构、Docker 和部署脚本。
- 不优先调整现有 FastAPI 路由路径、请求字段、响应字段和前端调用方式。
- 不直接把 `app/services/multi_agent/` demo 接入生产主链路。
- 不在没有接口基线和结构测试前批量搬迁目录。

## 已识别风险

- 当前 `app/router/review_task.py` 同时承担任务编排、并发调度、DB 状态、SSE 输出和 agent 调用，后续拆分必须保证 SSE 顺序和落库顺序不变。
- 当前文件上传接口中混有文档解析和 LLM 信息抽取，后续拆分要避免改变上传接口返回字段。
- 当前 RAG、Prompt、LLM 输出解析和风险字段语义属于高风险区域，必须保留失败兜底。
- PDF、OCR、复杂表格和版面定位的解析质量存在不确定性，需要独立评测。
- MCP 如果作为强依赖会占用上下文并增加失败点，后续应评估为可选工具能力。

## 当前进度

| 日期 | 事项 | 状态 | 说明 |
| --- | --- | --- | --- |
| 2026-05-09 | 初始化重构计划文档 | 已完成 | 新增根目录 `PLANS.md`，用于后续记录分步重构和开发进度。 |
| 2026-05-09 | 增加接口字段冻结规则 | 已完成 | 在 `AGENTS.md` 最醒目位置增加 FastAPI 既有接口入参、出参字段禁止更改规则。 |
| 2026-05-09 | 增加文档读取策略 | 已完成 | 在 `AGENTS.md` 增加进入任务前的文档读取要求。 |
| 2026-05-09 | 改版为 agent 架构重构计划 | 已完成 | 将原阶段计划改为以后端和 agent 解耦为核心的重构计划，并纳入会议记录。 |

## 阶段记录模板

后续每完成一个阶段或关键任务，按以下格式追加记录：

```text
### YYYY-MM-DD 阶段名称

- 改动范围：
- 未改动但相关的部分：
- 风险点：
- 验证方式：
- 验证结果：
- 未验证边界：
- 下一步：
```
