# PLANS.md

本文档用于记录合同审阅项目的架构重构计划、开发进度、阶段验收和风险状态。后续涉及分步开发或长期重构任务时，必须同步更新本文档。

## 重构定位

- 本轮重构重点是后端逻辑与 agent 能力逻辑完全解耦，不优先改动现有后端业务接口。
- 当前已存在的 FastAPI 接口入参字段、出参字段、SSE 事件结构全部冻结，禁止在重构中修改。
- 后续 backend 与 agent 很可能拆成两个独立服务；agent 端只通过自身接口接收参数、文件引用等业务参数并返回结构化能力结果。
- backend 不再持有或暴露供 agent 依赖的 LLM、model、OpenAI SDK 等实例，也不通过容器内网桥向 agent 传递 API key。
- 若 agent 执行模型调用需要密钥或模型配置，应由 agent 服务端通过自身配置或数据库访问能力获取，backend 只传递业务身份和任务上下文。
- 后端逻辑与 agent 能力逻辑需要完全解耦：后端负责接口、鉴权、任务、会话、落库和状态；agent 负责文档感知、解析、分块、RAG、skills、多 agent 编排、LLM 调用和结构化输出。
- `src/backend/` + `src/agent/` 作为目标架构方向可行；第一步先建立对应文件结构和边界，之后再通过契约层和适配层迁移主审阅链路。
- `app/services/multi_agent/` 当前仍按试验性实现看待，不能直接作为生产入口接入。
- 当前开发文档优先推进 agent 侧重构；backend 暂时只作为既有 FastAPI 字段来源、兼容包装层和 agent 能力调用方记录。
- Step 2 只处理当前代码已有字段和可推导字段，不纳入知识库版本、Langfuse trace、重向量化等后续新增能力。
- Step 2 的旧版本字段来源、字段映射和禁止项详见 `docs/LEGACY_AGENT_FIELD_BASELINE.md`，`PLANS.md` 只保留阶段计划和进度摘要。

## 当前对外接口基线

当前合同审阅能力对外主要暴露在 `app/router/review_task.py`，并由 `main_new.py` 注册到 `/api/review_task`。

| 接口 | 文件 | 当前职责 | 重构要求 |
| --- | --- | --- | --- |
| `POST /api/review_task/start_task` | `app/router/review_task.py` | 启动审阅任务，SSE 输出风险点和总结 | 路径、入参字段、SSE 字段保持不变，内部只能通过 agent 能力接口或适配层调用 agent |
| `POST /api/review_task/accept_risk_point` | `app/router/review_task.py` | 接受或取消接受风险点修订 | 保持后端结果处理接口，不下沉到 agent |
| `POST /api/review_task/accept_contract_file` | `app/router/review_task.py` | 修改合同文件整体修订状态 | 保持后端结果处理接口，不下沉到 agent |

相关但不属于主审阅 agent 入口的接口：

| 接口 | 文件 | 关系 |
| --- | --- | --- |
| `POST /api/chat/chat` | `app/router/chat.py` | 合同聊天 LLM 流式能力，后续应由 backend 调用 agent 聊天能力接口 |
| `POST /api/contract/upload` | `app/router/contract.py` | 文件上传、解析和合同信息抽取，后续应拆出文档感知层 |
| `POST /api/session/session_history_detail` | `app/router/session.py` | 读取审阅历史，字段必须保持兼容 |
| `POST /api/comparison_task/start` | `app/router/comparison_task.py` | 合同比对能力，当前不是 agent 审阅链路 |

## 目标职责边界

### backend 负责

- FastAPI 路由、鉴权、中间件、请求响应模型和接口兼容。
- 用户、会话、文件、审阅任务、审阅结果、比对结果等数据库读写。
- 任务状态流转、SSE 包装、接口错误码和现有前端兼容。
- 文件元数据、上传下载入口、权限校验和审阅结果持久化。
- 调用 agent 能力接口或本地过渡适配层，但不实例化 LLM、model、OpenAI SDK，不拼装 agent prompt，不执行 RAG 和 skills。

### agent 负责

- 文件存储前后的安全清洗、提示词注入防护和文档格式统一。
- DOC、DOCX、PDF、扫描件 PDF、普通 PDF 的解析路由。
- 图片、表格、页码、版面序号、源文本定位和纯文本映射。
- 语义分块、硬切块修复、分块定位标记和后续修改定位参数。
- RAG 检索、知识库版本返回、模型切换、重向量化和 Langfuse 链路追踪。
- skills 调用、冲突处理、多 agent 异步审阅、合并和仲裁。
- LLM 输出解析、失败兜底和结构化审阅结果。
- agent 服务端自主管理模型网关、模型配置读取、API key 获取和外部模型 SDK 实例。

### 依赖规则

- `backend` 只能调用 `agent` 暴露的能力接口、客户端适配器或过渡期本地 facade。
- `agent` 不允许反向依赖 FastAPI 路由、SQLAlchemy 模型、CRUD、鉴权或中间件。
- `agent` 返回结构化结果，由 `backend` 负责转换成现有 SSE 和数据库记录。
- `backend` 调用 `agent` 时只传当前 FastAPI 入参、登录用户、会话、文件记录和已存在处理流程能提供的业务参数，不传 API key、OpenAI client、LLM 实例或模型 SDK 对象。
- `agent` 如需访问模型配置或密钥，只能通过 agent 自己的配置读取或数据库访问边界完成。
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
    agent_client/
      review_client.py
      chat_client.py
      schemas.py
    infrastructure/
      db/
      redis/
      storage/
      repositories/

  agent/
    api/
      review_api.py
      chat_api.py
      health_api.py
    contracts/
      agent_request.py
      agent_response.py
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
    infrastructure/
      db/
      secrets/

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

### Step 1：后端与 agent 完全解耦并建立文件结构

- √ 建立 `src/backend/`、`src/agent/`、`src/shared/` 的基础目录结构。
- √ 在 `src/backend/agent_client/` 建立调用 agent 能力接口的客户端适配层位置。
- √ 在 `src/agent/api/` 建立 agent 对外能力接口位置，预留 review、chat、health 等入口。
- √ 在 `src/agent/contracts/` 建立 agent 能力接口请求和响应契约位置。
- √ 在 `src/agent/llm/` 和 `src/agent/infrastructure/` 建立模型网关、模型配置读取和密钥读取边界。
- √ 梳理当前 backend 中直接实例化 LLM、model、OpenAI SDK 的位置，形成迁移清单。
- √ 明确 backend 禁止向 agent 传递 API key、OpenAI client、LLM 实例和模型 SDK 对象。
- √ 明确 agent 不能 import backend 的 router、schema、CRUD、SQLAlchemy model、鉴权和中间件。
- √ 完成目录结构和依赖边界检查，不改现有 FastAPI 对外字段。

### Step 2：现有字段来源核对与 agent 完整业务字段契约

详细字段来源、字段映射和禁止项已经迁移到 `docs/LEGACY_AGENT_FIELD_BASELINE.md`。该文档记录旧版本 `app/` 逻辑下的字段基线，新版本 `src/` 下 backend 与 agent 的契约设计必须参照该文档。

- √ 完成审阅能力入参来源核对。
- √ 完成聊天能力入参来源核对。
- √ 完成文件感知与合同信息抽取入参来源核对。
- √ 完成 agent 返回字段与现有后端消费点核对。
- √ 明确 Step 2 不设计知识库版本、Langfuse trace、重向量化、模型配置透传和 SDK 实例透传。
- √ 将 Step 2 详细核对结果迁移到 `docs/LEGACY_AGENT_FIELD_BASELINE.md`。

Step 2 结论只允许用于当前基础重构：agent 入参和返回字段必须来自现有 FastAPI 入参、登录用户、会话记录、文件记录和现有流程中已经可获得的字段，不能凭空新增字段。

### Step 3：agent 完整契约层设计

详细设计见 `docs/AGENT_CONTRACT_DESIGN.md`。Step 3 的目标是建立完整可用的 agent 契约数据结构，而不是只制定裁剪版入参。

- √ 形成 Step 3 设计文档，明确 agent 契约层不是裁剪版参数集合，而是参照旧版业务链路建立完整可用的数据结构。
- √ 设计通用上下文结构：用户、会话、合同文件、任务、文档内容引用、错误和降级信息。
- √ 设计审阅能力结构：`ReviewRequest`、`ReviewExecutionOptions`、`ReviewRiskItem`、`ReviewResponse`、`ReviewStreamEvent`。
- √ 设计聊天能力结构：`ChatRequest`、`ChatMessage`、`ChatResponseChunk`、`ChatDonePayload`、`ChatErrorPayload`。
- √ 设计文件感知结构：`DocumentIntakeRequest`、`ParsedDocument`、`ContractInfoExtraction`、`DocumentIntakeResponse`。
- √ 设计文档和 RAG 结构：`DocumentBlock`、`SourceLocation`、`KnowledgeHit`，知识库版本仍不在当前基础重构阶段引入。
- 【】补充契约层结构测试，不接真实模型和外部服务。

### Step 4：文档感知与存储安全

- 【】设计存储阶段提示词注入防护规则，避免合同正文影响系统 prompt 和工具调用。
- 【】设计 DOC、DOCX 统一输出为 DOCX 的格式归一流程。
- 【】设计 PDF 物理类型判断逻辑，将扫描件 PDF 和普通 PDF 分流。
- 【】设计文件感知层输出结构，保留文件类型、页码、版面序号和解析置信度。
- 【】使用样例文件做结构验证，确认不改变上传接口返回字段。

### Step 5：解析与失败回退链路

- 【】验证当前 DOC、DOCX 解析精度，并评估 `python-docx` 等替换方案。
- 【】验证普通 PDF 使用 MinerU + OCR + 文字处理的解析效果。
- 【】验证 DeepSeek OCR 对复杂表格的识别精度，判断是否需要 AI 补全。
- 【】将图片、表格等版面元素清洗为纯文本，并记录映射回源文档的位置。
- 【】设计空文本、低置信度、解析异常、外部服务不可用时的失败回退策略。
- 【】形成解析评测记录和 fallback 策略说明。

### Step 6：语义分块与定位

- 【】设计替代纯长度切块的语义分块流程。
- 【】评估轻量模型用于保证分块语义完整的成本、速度和稳定性。
- 【】设计 AI 修复硬语义切块造成语义损失的流程。
- 【】在切块结果中保留页码、版面序号、源文本定位和修改定位参数。
- 【】补充分块完整性和定位结构测试。

### Step 7：RAG、模型网关与链路追踪

- 【】设计 RAG 返回结构，除条文外必须返回 RAG 系统版本和知识库版本。
- 【】设计模型网关，支持审阅模型、聊天模型、轻量分块模型和 embedding 模型切换。
- 【】设计重向量化流程，支持模型切换后的知识库重建。
- 【】设计 Langfuse trace 事件，覆盖文档感知、解析、分块、RAG、skills、agent 审阅、合并仲裁。
- 【】设计自动更新和人工更新并存的 RAG 更新流程，先例反哺必须经人工确认。
- 【】完成不依赖自然语言措辞的结构验证。

### Step 8：skills 与多 agent 编排

- 【】确定多 agent 设计范式，优先考虑异步 specialist 审阅后合并仲裁。
- 【】设计 specialist agent 的输入、输出、停止条件和失败兜底。
- 【】设计冲突处理 skills，用于处理多个 agent 审阅意见不一致的情况。
- 【】设计 RAG、skills 和审阅 agent 的上下文传递边界，避免上下文无限膨胀。
- 【】明确 MCP 不作为主审阅链路强依赖时的工具调用策略。
- 【】使用假模型跑通完整结构链路。

### Step 9：后端适配层接入

- 【】设计 backend 到 agent 的适配层，将现有 `ReviewTaskCreateRequest` 转换为 agent 能力接口入参。
- 【】将 agent 输出转换成现有 `ReviewTaskSSEResponse` 和审阅结果落库字段。
- 【】保持 `/api/review_task/start_task` 路径、入参字段、SSE 字段和事件顺序不变。
- 【】保持审阅任务状态流转、并发控制和结果落库顺序兼容。
- 【】确认 backend 适配层没有实例化 LLM、model、OpenAI SDK 或 agent 内部工具。
- 【】完成 SSE 字段回归、落库顺序检查和基础链路验证。

### Step 10：旧链路收敛与文档对齐

- 【】清理或明确标记 `app/services/multi_agent/` 中仍属于试验性链路的实现。
- 【】梳理旧 `ContractReviewService` 中 prompt 拼装、RAG、解析和 LLM 调用的迁移状态。
- 【】迁移或隔离 backend 中直接调用 `init_llm`、`AsyncClient`、OpenAI SDK 和模型配置的逻辑。
- 【】更新过期项目结构、启动方式、依赖入口和开发流程说明。
- 【】形成保留、迁移、废弃清单。
- 【】执行 `uv run pytest` 或与本阶段直接相关的最小测试。

## 迁移策略

- 第一阶段先建立 backend、agent、shared 的文件结构和依赖边界，不改现有接口字段和业务表结构。
- 第二阶段只基于现有 FastAPI 入参、登录用户、会话、文件记录和现有处理流程核对 agent 能力接口出入参，不设计后续新增字段。
- 第三阶段开始优先推进 agent 契约、文档感知、解析、分块、RAG、skills 和多 agent 编排。
- 第四阶段在 agent 模块中做可运行的最小链路，用假模型和样例文本验证结构。
- 第五阶段逐步把 `ContractReviewService` 中的 prompt 拼装、RAG、解析、LLM 调用和 OpenAI SDK 实例迁移到 agent 内部模块。
- 第六阶段通过 backend 的 agent client 适配层把 agent 输出转换成现有 `ReviewTaskSSEResponse` 和审阅结果落库字段。
- 第七阶段再评估是否将 `main_new.py`、`app/router/`、`app/schemas/` 迁移到 `src/backend/`。

## 不在本轮优先处理

- 不优先修改用户、鉴权、中间件、数据库结构、Docker 和部署脚本。
- 不优先调整现有 FastAPI 路由路径、请求字段、响应字段和前端调用方式。
- 不直接把 `app/services/multi_agent/` 中未完成验收的试验性实现接入生产主链路。
- 不在没有接口基线和结构测试前批量搬迁目录。
- 不允许在 backend 新增 LLM、model、OpenAI SDK、Prompt、RAG、skills 相关实例化逻辑。

## 已识别风险

- 当前 `app/router/review_task.py` 同时承担任务编排、并发调度、DB 状态、SSE 输出和 agent 调用，后续拆分必须保证 SSE 顺序和落库顺序不变。
- 当前文件上传接口中混有文档解析和 LLM 信息抽取，后续拆分要避免改变上传接口返回字段。
- 当前 backend 代码中仍存在直接实例化 LLM、AsyncClient、OpenAI SDK 和模型配置调用的逻辑，需要第一阶段形成迁移清单。
- 当前 RAG、Prompt、LLM 输出解析和风险字段语义属于高风险区域，必须保留失败兜底。
- agent 服务未来可能独立读取数据库中的模型配置和密钥，需要单独设计权限边界，避免扩大密钥暴露面。
- PDF、OCR、复杂表格和版面定位的解析质量存在不确定性，需要独立评测。
- MCP 如果作为强依赖会占用上下文并增加失败点，后续应评估为可选工具能力。

## 当前进度

| 日期 | 事项 | 状态 | 说明 |
| --- | --- | --- | --- |
| 2026-05-09 | 初始化重构计划文档 | 已完成 | 新增根目录 `PLANS.md`，用于后续记录分步重构和开发进度。 |
| 2026-05-09 | 增加接口字段冻结规则 | 已完成 | 在 `AGENTS.md` 最醒目位置增加 FastAPI 既有接口入参、出参字段禁止更改规则。 |
| 2026-05-09 | 增加文档读取策略 | 已完成 | 在 `AGENTS.md` 增加进入任务前的文档读取要求。 |
| 2026-05-09 | 改版为 agent 架构重构计划 | 已完成 | 将原阶段计划改为以后端和 agent 解耦为核心的重构计划，并纳入会议记录。 |
| 2026-05-09 | 明确 backend 与 agent 完全服务解耦方向 | 已完成 | Step 1 调整为先建立 backend、agent、shared 文件结构和依赖边界，并禁止 backend 持有 agent 侧 LLM / OpenAI SDK 实例。 |
| 2026-05-09 | 完成 Step 1 目录边界与调用点扫描 | 已完成 | 新增 `src/` 目标目录说明和 `docs/AGENT_BACKEND_DECOUPLING_SCAN.md`，记录 backend 中 LLM、OpenAI SDK、model_config 迁移清单。 |
| 2026-05-09 | 调整 Step 2 字段来源规则 | 已完成 | Step 2 改为先核对现有 FastAPI 字段来源和 agent 完整业务字段契约，移除知识库版本、trace 等后续新增能力。 |
| 2026-05-09 | 完成 Step 2.1 审阅能力入参来源核对 | 已完成 | 已确认审阅 agent 业务入参只能来自 `ReviewTaskCreateRequest`、`current_user.id`、会话 `file_id` 和合同文件记录，禁止透传模型配置或 SDK 实例。 |
| 2026-05-09 | 完成 Step 2.2 聊天能力入参来源核对 | 已完成 | 已确认聊天 agent 业务入参只能来自 `ChatRequest`、可选 `current_user.id`、会话 `file_id` 和历史消息，且必须兼容 `user_id=None`。 |
| 2026-05-09 | 完成 Step 2.3 文件感知入参来源核对 | 已完成 | 已确认文件感知 agent 业务入参只能来自 `UploadFile` 保存后的文件引用、`current_user.id`、文件名和文件类型，上传响应字段保持不变。 |
| 2026-05-09 | 完成 Step 2.4 agent 返回字段映射核对 | 已完成 | 已确认审阅、聊天、文件感知 agent 输出必须映射到现有 SSE、落库字段和上传响应字段，不新增返回结构。 |
| 2026-05-09 | 完成 Step 2.5 本阶段禁止项核对 | 已完成 | 已确认 Step 2 不设计知识库版本、Langfuse trace、重向量化、模型配置透传和 SDK 实例透传。 |
| 2026-05-09 | 迁移 Step 2 详细字段基线 | 已完成 | 已将 Step 2 详细核对内容迁移到 `docs/LEGACY_AGENT_FIELD_BASELINE.md`，`PLANS.md` 只保留必要摘要。 |
| 2026-05-09 | 完成 Step 3 契约层设计文档 | 已完成 | 新增 `docs/AGENT_CONTRACT_DESIGN.md`，明确 agent 契约应承接旧版完整业务字段，覆盖审阅、聊天、文件感知、文档块和 RAG 命中结构。 |

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
