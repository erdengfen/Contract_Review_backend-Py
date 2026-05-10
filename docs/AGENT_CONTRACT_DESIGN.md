# Step 3 Agent 完整契约层设计

本文档用于定义新版本 `src/agent/contracts/` 后续要实现的数据结构。设计依据是 `docs/LEGACY_AGENT_FIELD_BASELINE.md` 中记录的旧版本 `app/` 业务链路字段，不是脱离当前业务的裁剪版参数草案。

## 设计定位

- Step 3 要建立完整可用的数据结构，覆盖审阅、聊天、文件感知和文档解析后的内部结构。
- 这些结构是 backend 调用 agent 能力时的契约层，不直接改变现有 FastAPI 路径、入参字段、出参字段或 SSE 事件字段。
- 当前旧版本字段能够提供的业务参数应完整承接，不因为先做基础重构就主动裁剪。
- backend 只负责把旧 FastAPI 入参、登录用户、会话记录、文件记录和任务记录组装成 agent 契约。
- agent 契约中禁止出现 API key、OpenAI client、LLM 实例、model SDK 对象和 backend 内部 CRUD、router、SQLAlchemy model 实例。
- 知识库版本、Langfuse trace、重向量化参数属于后续增强能力，不进入当前 Step 3 基础契约。

## 目标文件结构

后续代码实现建议落在以下位置：

```text
src/agent/contracts/
  common.py
  document.py
  review.py
  chat.py
  rag.py
```

其中 `common.py` 放通用快照、错误和来源定位结构；`document.py` 放文件感知和解析结构；`review.py` 放合同审阅结构；`chat.py` 放合同聊天结构；`rag.py` 放当前可用的检索命中结构。

## 通用结构

### SessionSnapshot

用于保存旧版 `app.models.session_message.Session` 中 agent 能力可能需要的会话快照。

- `session_id`：来源于 `Session.id` 或旧接口请求中的 `session_id`。
- `file_id`：来源于 `Session.file_id`。
- `user_id`：来源于 `Session.user_id`，聊天未登录场景可为 `None`。
- `title`：来源于 `Session.title`。
- `session_type`：来源于 `Session.session_type`。
- `created_at`：来源于 `Session.created_at`。
- `updated_at`：来源于 `Session.updated_at`。

### ContractFileSnapshot

用于保存旧版 `app.models.contract.ContractFile` 的完整业务字段快照。

- `file_id`：来源于 `ContractFile.id`。
- `user_id`：来源于 `ContractFile.user_id`。
- `type`：来源于 `ContractFile.type`，当前存在 `uploaded`、`parsed` 等值。
- `title`：来源于 `ContractFile.title`。
- `file_path`：来源于 `ContractFile.file_path`。
- `file_type`：来源于 `ContractFile.file_type`。
- `upload_time`：来源于 `ContractFile.upload_time`。
- `status`：来源于 `ContractFile.status`。
- `party_a`：来源于 `ContractFile.party_a`。
- `party_b`：来源于 `ContractFile.party_b`。
- `amount`：来源于 `ContractFile.amount`。
- `is_accepted`：来源于 `ContractFile.is_accepted`。
- `contract_content_path`：来源于 `ContractFile.contract_content_path`。
- `contract_type_id`：来源于 `ContractFile.contract_type_id`。
- `review_position`：来源于 `ContractFile.review_position`。
- `file_url`：不是数据库字段，可由 backend adapter 按旧上传响应规则从 `user_id` 和 `title` 计算。

### ReviewTaskSnapshot

用于保存旧版 `app.models.review.ReviewTask` 与 `ReviewTaskCreateRequest` 合并后的任务快照。

- `task_id`：来源于 `ReviewTask.id`。
- `session_id`：来源于 `ReviewTask.session_id`。
- `file_id`：来源于 `ReviewTask.file_id`。
- `user_id`：来源于 `ReviewTask.user_id`。
- `type`：来源于 `ReviewTask.type`，当前创建链路可能为空，结构上保留。
- `stance`：来源于 `ReviewTask.stance` 或 `ReviewTaskCreateRequest.stance`。
- `intensity`：来源于 `ReviewTask.intensity` 或 `ReviewTaskCreateRequest.intensity`。
- `effective_intensity`：来源于旧审阅调用实际行为；当前旧链路固定传入 `"标准"`，用于兼容行为记录。
- `contract_type`：来源于 `ReviewTask.contract_type` 或 `ReviewTaskCreateRequest.contract_type`。
- `description`：来源于 `ReviewTask.description` 或 `ReviewTaskCreateRequest.description`。
- `status`：来源于 `ReviewTask.status`。
- `max_concurrent`：来源于 `ReviewTaskCreateRequest.max_concurrent`。
- `created_at`：来源于 `ReviewTask.created_at`。
- `completed_at`：来源于 `ReviewTask.completed_at`。

### DocumentContentRef

用于表达合同正文的可用来源，支持未来 agent 独立服务和当前本地迁移两种部署方式。

- `file_path`：来源于 `ContractFile.file_path` 或上传保存路径。
- `file_type`：来源于 `ContractFile.file_type` 或上传文件后缀。
- `contract_content_path`：来源于 `ContractFile.contract_content_path`。
- `contract_content`：来源于当前旧链路读取 `contract_content_path` 后得到的正文内容，作为过渡期可选字段。
- `filename`：来源于 `UploadFile.filename` 或 `ContractFile.title`。
- `title`：来源于 `ContractFile.title`。
- `content_source`：由 adapter 标记当前使用 `contract_content`、`contract_content_path` 或 `file_path`。

### AgentError

用于 agent 内部错误和降级结果，不直接改变旧 SSE 错误结构。

- `code`：错误码，由 agent 内部定义。
- `message`：可展示错误信息，不得包含密钥、token 或合同全文。
- `stage`：错误阶段，如 `document_intake`、`chunking`、`rag`、`review`、`chat`。
- `recoverable`：是否可降级继续。
- `details`：结构化诊断信息，只允许放非敏感摘要。

## 文档结构

### SourceLocation

用于记录文本片段回溯到源文档的位置。

- `file_path`：源文件路径。
- `contract_content_path`：解析后正文路径。
- `page_number`：页码，无法识别时可为 `None`。
- `block_index`：文档块序号。
- `layout_index`：版面元素序号。
- `start_offset`：在纯文本中的起始偏移。
- `end_offset`：在纯文本中的结束偏移。
- `element_type`：文本、表格、图片 OCR、标题、页眉页脚等。

### DocumentBlock

用于文档解析、语义分块、RAG 和后续修改定位。

- `block_id`：分块唯一标识，建议由文件 ID、页码、块序号组合生成。
- `text`：分块文本。
- `normalized_text`：清洗后的文本。
- `source_location`：对应 `SourceLocation`。
- `section_title`：所属章节标题。
- `page_number`：冗余页码，便于快速检索和排序。
- `block_index`：分块顺序。
- `token_count`：估算 token 数。
- `char_count`：字符数。
- `metadata`：非敏感扩展信息，用于解析器和分块器内部传递。

### ParsedDocument

用于文件感知和解析阶段输出。

- `filename`：来源于上传文件名或合同标题。
- `file_type`：来源于文件后缀或归一化后的类型。
- `file_path`：原文件保存路径。
- `normalized_file_path`：格式归一后的文件路径，如 DOC 转 DOCX 后的路径。
- `contract_content`：解析出的合同正文。
- `contract_content_path`：正文写入路径。
- `blocks`：`DocumentBlock` 列表。
- `parser_name`：实际使用的解析器名称。
- `parse_status`：解析状态，如 `success`、`partial`、`failed`。
- `warnings`：非敏感解析告警。

## 文件感知结构

### DocumentIntakeRequest

用于 agent 文件感知能力的完整入参。

- `file_id`：来源于 backend 文件记录，允许为空以兼容接线前的结构测试。
- `user_id`：来源于 `current_user.id`，用于业务上下文；文件权限控制仍由 backend 负责。
- `filename`：来源于 `UploadFile.filename`。
- `file_type`：来源于 `UploadFile.filename` 后缀。
- `save_path`：由 backend 提供的稳定本地路径、共享卷路径或文件服务落地路径。
- `storage_uri`：由 backend 提供的对象存储或文件服务 URI，可选。

### FileReferenceSnapshot

用于 agent 感知层记录可读取文件引用和文件级指纹，不包含 backend 存储决策字段。

- `file_id`：来源于 backend 文件记录。
- `original_filename`：来源于上传文件名。
- `declared_file_type`：来源于 backend 传入的声明文件类型。
- `detected_file_type`：来源于 agent 基于文件头或容器结构识别出的文件类型。
- `save_path`：backend 提供的稳定文件路径。
- `storage_uri`：backend 提供的对象存储或文件服务 URI。
- `size_bytes`：agent 基于文件引用读取到的文件大小。
- `sha256`：agent 基于文件引用计算出的文件指纹。

当前接线状态：

- 旧版本文件接收接口仍是 `POST /api/contract/upload`，由 `app/router/contract.py` 接收 `UploadFile`。
- 新版本 `src/agent/document_intake/` 感知层尚未接入 FastAPI 上传接口。
- 当前 agent 感知层假设 backend 已经完成文件保存，并通过 `save_path` 传入稳定文件引用。
- 新 backend 侧真实文件写入、命名冲突处理、共享存储路径生成和 DB 文件记录写入仍待实现。
- agent 感知层不接收文件流、不写入原始文件、不生成安全文件名、不执行格式转换、不抽取正文。

### ContractInfoExtraction

用于承接旧版 LLM 合同信息抽取结果。

- `party_a`：甲方名称，来源于旧版 `parse_contract_info`。
- `party_b`：乙方名称，来源于旧版 `parse_contract_info`。
- `amount`：合同金额，来源于旧版 `parse_contract_info` 后的 float 转换。

### DocumentIntakeResponse

用于 agent 文件感知能力返回给 backend。

- `parsed_document`：对应 `ParsedDocument`。
- `contract_info`：对应 `ContractInfoExtraction`。
- `errors`：`AgentError` 列表。
- `fallback_used`：是否使用降级解析。

backend 仍负责创建合同文件记录，并保持上传接口响应字段为 `file_id`、`title`、`file_path`、`file_type`、`file_url`、`party_a`、`party_b`、`amount`。

## 解析前文件链路

推荐链路是先存储、再解析：

1. backend 接收上传文件流。
2. backend 完成权限校验、文件名安全化、原始文件写入共享存储或对象存储。
3. backend 写入或更新文件元数据，形成 `file_id`、`file_path`、`file_type`、`title`、`user_id` 等记录。
4. backend 调用 agent 文件感知能力，传入 `DocumentIntakeRequest`，其中 `save_path` 指向已经保存的文件。
5. agent 感知层读取文件头、大小、hash、文件类型线索，输出 `DocumentSensingResult`。
6. Step 5 解析层根据 `DocumentSensingResult.route` 执行 DOC 归一化、DOCX 解析、PDF 文本解析或 OCR。

不推荐先解析后存储。原因是解析、OCR 和格式转换都需要稳定可追踪的原始文件来源；先存储可以保留证据链、支持失败重试、支持异步处理，也避免上传请求过程中直接执行耗时解析。

如果 backend 与 agent 拆成独立服务，可以共享同一个数据库和同一套文件存储，但需要明确权限边界：

- DB 可以共享，但建议 agent 只读取自身所需的文件记录、模型配置和密钥配置，不反向依赖 backend 的 ORM model、CRUD 或业务服务实例。
- 文件可以通过共享卷、NFS、对象存储或内部文件服务共享；生产上更推荐对象存储或文件服务，避免把某个容器本地路径当成跨服务稳定路径。
- 如果实际文件存储逻辑落在 backend，agent 侧可以只保留感知、解析、分块和审阅能力；backend 传给 agent 的应是稳定文件引用，而不是文件流或 backend 本机私有路径。

## 审阅结构

### ReviewExecutionOptions

用于保存旧审阅链路中的执行参数和兼容行为。

- `max_concurrent`：来源于 `ReviewTaskCreateRequest.max_concurrent`。
- `chunk_max_length`：来源于旧版 `split_text_by_length(contract_content, max_length=4000)`。
- `ordered_emit`：来源于旧版按 chunk 顺序输出 SSE 的行为，默认 `True`。
- `continue_on_chunk_error`：来源于旧版单 chunk 异常时返回空列表继续处理的行为，默认 `True`。
- `requested_intensity`：来源于 `ReviewTaskCreateRequest.intensity`。
- `effective_intensity`：来源于旧版实际调用 `review_contract` 时的强制 `"标准"`。
- `stance`：来源于 `ReviewTaskCreateRequest.stance`。
- `contract_type`：来源于 `ReviewTaskCreateRequest.contract_type`。
- `description`：来源于 `ReviewTaskCreateRequest.description`。

### ReviewRequest

用于 backend 调用 agent 审阅能力。

- `task`：对应 `ReviewTaskSnapshot`。
- `session`：对应 `SessionSnapshot`。
- `contract`：对应 `ContractFileSnapshot`。
- `document`：对应 `DocumentContentRef`。
- `options`：对应 `ReviewExecutionOptions`。
- `prebuilt_blocks`：过渡期可选字段；如果 backend 已经按旧逻辑切块，可传入 `DocumentBlock`，长期应由 agent 文档层和分块层生成。

### ReviewRiskItem

用于承接 agent 输出的单条风险点。字段要覆盖当前落库字段和旧解析器已经能解析出的完整字段。

- `index`：风险点全局序号，由 agent 或 backend adapter 按输出顺序确定。
- `position`：来源于旧解析器的 `修改点X`。
- `original_content`：当前落库字段，必须保留。
- `risk_analysis`：当前落库字段，必须保留。
- `risk_level`：当前落库字段，必须保留。
- `suggested_content`：当前落库字段，必须保留。
- `reason`：来源于旧解析器的 `修改理由`。
- `risk_type`：来源于旧解析器的 `风险类型`。
- `priority`：来源于旧解析失败兜底结构，正常链路可为空。
- `action`：来源于旧解析失败兜底结构，正常链路可为空。
- `source_block_ids`：对应 `DocumentBlock.block_id`，用于后续定位。
- `knowledge_hit_ids`：对应 `KnowledgeHit.hit_id`，用于后续解释和审计。
- `parser_status`：标记 `parsed`、`fallback` 或 `failed`。

backend 现阶段只把 `original_content`、`risk_analysis`、`risk_level`、`suggested_content` 写入 `CRUDReviewResult.create_review_result`，其他字段保留在 agent 契约和后续扩展链路中。

### ReviewSummary

用于 agent 可选返回总结，但不改变当前 backend 的 SSE 总结兼容策略。

- `total_issues`：风险点数量。
- `overall_risk`：整体风险等级。
- `summary`：审阅摘要。
- `suggestion`：处理建议。

### ReviewResponse

用于一次审阅能力调用的完整返回。

- `task_id`：来源于 `ReviewTaskSnapshot.task_id`。
- `session_id`：来源于 `ReviewTaskSnapshot.session_id`。
- `file_id`：来源于 `ReviewTaskSnapshot.file_id`。
- `items`：`ReviewRiskItem` 列表。
- `summary`：可选 `ReviewSummary`。
- `errors`：`AgentError` 列表。
- `fallback_used`：是否使用降级解析或降级审阅。

### ReviewStreamEvent

用于 agent 内部流式返回，再由 backend 映射为旧版 `ReviewTaskSSEResponse`。

- `event`：允许 `message`、`end`、`error`。
- `data`：结构化数据。
- `sequence`：输出顺序。

backend 对外仍保持旧 SSE：`event="message"` 时输出落库后的 `ReviewResult.dict()`；`event="end"` 时输出 `type`、`summary`、`suggestion`；`event="error"` 时输出 `data={"message": ...}`。

## 聊天结构

### ChatMessage

用于承接旧版 `message` 表字段和当前 history 结构。

- `message_id`：来源于 `Message.id`，当前 `history` 只有 `role`、`content` 时可为空。
- `session_id`：来源于 `Message.session_id`。
- `role`：来源于 `Message.role`，进入 agent 时规范为 `user` 或 `assistant`。
- `content`：来源于 `Message.content`。
- `parent_id`：来源于 `Message.parent_id`。
- `message_index`：来源于 `Message.message_index`。
- `created_at`：来源于 `Message.created_at`。

### ChatRequest

用于 backend 调用 agent 聊天能力。

- `session_id`：来源于 `ChatRequest.session_id`。
- `user_id`：来源于可选登录用户，未登录场景可为 `None`。
- `file_id`：来源于会话记录 `Session.file_id`。
- `content`：来源于 `ChatRequest.content`。
- `parent_id`：来源于 `ChatRequest.parent_id`。
- `session`：对应 `SessionSnapshot`。
- `contract`：可选 `ContractFileSnapshot`，由 backend adapter 通过 `file_id` 查询得到时传入。
- `history`：`ChatMessage` 列表；如果沿用旧函数结果，至少要包含 `role` 和 `content`。
- `context_window_messages`：来源于旧版 `getattr(session, "max_context_length", 5) * 2`，当前默认 10。

### ChatResponseChunk

用于 agent 聊天流式内容。

- `content`：模型输出增量。
- `role`：固定为 `assistant`。
- `sequence`：流式片段顺序。

### ChatDonePayload

用于 agent 聊天完成事件。

- `full_content`：完整助手回复。
- `role`：固定为 `assistant`。

backend 仍负责保存 assistant 消息，并在旧 SSE done 结构中补充 `message_id`。

### ChatErrorPayload

用于 agent 聊天错误事件。

- `error`：错误信息，不包含密钥和敏感原文。
- `stage`：错误阶段。

backend 对外仍映射为旧版 `type="error"`、`error` 字段。

## RAG 结构

### KnowledgeHit

用于承接当前 `app.rag.schemas.RetrievalHit` 已有字段。

- `hit_id`：建议由 `source_collection` 和 `record_id` 组合生成。
- `source_collection`：来源于 `RetrievalHit.source_collection`。
- `record_id`：来源于 `RetrievalHit.record_id`。
- `title`：来源于 `RetrievalHit.title`。
- `content`：来源于 `RetrievalHit.content`。
- `score`：来源于 `RetrievalHit.score`。
- `article_no`：来源于 `RetrievalHit.article_no`。
- `rule_type`：来源于 `RetrievalHit.rule_type`。
- `source_type`：来源于 `RetrievalHit.source_type`。
- `payload`：来源于 `RetrievalHit.payload`。

当前 Step 3 不加入知识库版本字段。后续如果需要返回 RAG 系统版本和知识库版本，应在 RAG 专项阶段单独扩展，并评估是否影响 backend adapter。

## 字段禁区

以下字段或对象禁止出现在 backend 到 agent 的业务契约中：

- `api_key`
- `model_config`
- `OpenAI client`
- `AsyncClient`
- `LLM 实例`
- `model SDK 对象`
- `SQLAlchemy Session`
- `SQLAlchemy model 实例`
- `FastAPI Request`
- `Depends` 依赖对象
- `CRUD` 实例或函数引用

## 映射原则

- backend adapter 可以从旧版 FastAPI 请求、登录用户、会话记录、任务记录和合同文件记录构造完整契约。
- agent response 不直接等于旧版 FastAPI response，必须由 backend adapter 映射回旧 SSE、上传响应和落库字段。
- 新契约允许比旧对外响应更完整，但旧 FastAPI 对外字段不允许新增、删除或改名。
- agent 内部扩展字段如果没有旧版来源，不能进入当前基础契约；确需新增时必须单独进入后续阶段。

## Step 3 验收标准

- 后续 `src/agent/contracts/` 代码实现应覆盖本文档列出的结构。
- 每个契约结构都应有清晰中文注释说明字段来源和使用边界。
- 契约结构测试只验证字段、默认值、序列化和禁止字段，不连接真实模型、数据库、Redis、MCP 或外部 OCR。
- 测试必须证明现有审阅、聊天、上传三条旧业务链路的字段都能被完整承接。
