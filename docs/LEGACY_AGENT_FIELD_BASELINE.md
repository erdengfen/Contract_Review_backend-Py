# 旧版本 Agent 字段基线

本文档记录当前旧版本 `app/` 目录下 FastAPI、CRUD、文件记录和 LLM 调用链路中已经存在的字段来源、字段映射和禁止项。

重构过程中，`src/` 下新版本 backend 与 agent 的字段设计必须参照本文档。本文档不是新接口扩展清单，不允许把这里没有来源的字段直接加入基础重构契约。

## 文档定位

- 旧版本依赖 `app/` 下路由、schema、CRUD、model 和 service 逻辑。
- 新版本重构在 `src/` 下开发，并逐步形成 `src/backend/`、`src/agent/`、`src/shared/` 的边界。
- 当前已存在的 FastAPI 入参字段、出参字段、SSE 事件字段必须保持兼容。
- backend 调用 agent 时只能传递当前 FastAPI 入参、登录用户、会话记录、文件记录和现有流程中已经能得到的业务字段。
- backend 不允许向 agent 传递 `model_config`、API key、OpenAI client、LLM 实例或模型 SDK 对象。
- 知识库版本、Langfuse trace、重向量化等属于后续新增能力，不属于当前旧版本字段基线。

## Step 2：现有字段来源核对与 Agent 完整业务字段契约

本步骤只允许使用当前 FastAPI 接口、登录用户、会话、文件记录和现有处理流程中已经存在的字段。禁止凭空新增 `trace`、知识库版本、重向量化参数、模型配置、API key 或 SDK 实例字段。

### Step 2.1：审阅能力入参来源

- √ 核对 `POST /api/review_task/start_task` 的请求字段：`session_id`、`stance`、`intensity`、`description`、`contract_type`、`max_concurrent`。
- √ 核对 `user_id` 来源：`current_user.id`，由 `get_current_user` 依赖提供。
- √ 核对 `file_id` 来源：通过 `request.session_id` 查询会话后获得 `session.file_id`，当前创建 `ReviewTask` 时写入 `review_task.file_id`。
- √ 核对文件内容来源：通过 `review_task.file_id` 查询合同文件，当前可用字段为 `contract.file_path`、`contract.file_type`、`contract.contract_content_path`。
- √ 核对审阅文本来源：当前代码从 `contract.contract_content_path` 读取 `contract_content`，后续 agent 入参应优先使用文件引用或内容引用，不能凭空构造文本。
- √ 核对审阅立场来源：`request.stance` 或落库后的 `review_task.stance`。
- √ 核对审阅尺度来源：`request.intensity` 或落库后的 `review_task.intensity`；当前调用审阅服务时写死 `"标准"`，后续修正前必须确认兼容风险。
- √ 核对合同类型来源：`request.contract_type` 或落库后的 `review_task.contract_type`。
- √ 核对审查需求来源：`request.description`；当前主审阅服务未实际使用，Step 2 只记录可用来源，不强行纳入必填入参。
- √ 核对并发参数来源：`request.max_concurrent`；当前由 backend 控制并发，若后续下沉 agent，需要单独确认行为兼容。

#### Step 2.1 核对结论

- agent 审阅能力完整业务入参字段只能来自现有字段：`session_id`、`user_id`、`file_id`、`contract_content_path`、`file_path`、`file_type`、`stance`、`intensity`、`contract_type`、`description`。
- `session_id` 来源于 `ReviewTaskCreateRequest.session_id`。
- `user_id` 来源于 `current_user.id`。
- `file_id` 来源于 `CRUDReviewTask.create_review_task` 内部通过 `request.session_id` 查询到的 `session.file_id`，并写入 `review_task.file_id`。
- `contract_content_path`、`file_path`、`file_type` 来源于 `CRUDContract.get_contract_file(db, review_task.file_id)` 返回的合同文件记录。
- `stance`、`intensity`、`contract_type`、`description` 来源于 `ReviewTaskCreateRequest`，并已落库到 `review_task`。
- `max_concurrent` 当前属于 backend 并发调度参数，不建议作为 agent 审阅业务必填入参；若后续由 agent 负责并发，需要单独确认兼容行为。
- 当前代码读取 `request.intensity` 并落库，但调用 `ContractReviewService.review_contract` 时传入固定值 `"标准"`；后续重构不能直接改变该行为，必须先确认前端和现有结果兼容。
- 当前 backend 不应再向 agent 传递 `model_config`、API key、OpenAI client、LLM 实例或模型 SDK 对象；模型选择和密钥读取由 agent 侧负责。

### Step 2.2：聊天能力入参来源

- √ 核对 `POST /api/chat/chat` 的请求字段：`session_id`、`content`、`parent_id`。
- √ 核对 `user_id` 来源：`current_user.id`；当前接口使用 `optional_get_current_user`，因此需要兼容未登录或空用户场景。
- √ 核对 `file_id` 来源：通过 `request.session_id` 查询会话后获得 `session.file_id`。
- √ 核对用户 query 来源：`request.content`。
- √ 核对父消息来源：`request.parent_id`。
- √ 核对历史消息来源：当前通过 `get_message_history_as_dicts(db, session.id)` 获取，字段为 `role`、`content`。
- √ 核对上下文窗口来源：当前通过 `getattr(session, "max_context_length", 5) * 2` 截断历史消息。

#### Step 2.2 核对结论

- agent 聊天能力完整业务入参字段只能来自现有字段：`session_id`、`user_id`、`file_id`、`content`、`parent_id`、`history`。
- `session_id` 来源于 `ChatRequest.session_id`。
- `content` 来源于 `ChatRequest.content`，对应 agent 聊天 query。
- `parent_id` 来源于 `ChatRequest.parent_id`，当前只用于保存用户消息，未参与模型上下文拼装。
- `user_id` 来源于 `current_user.id`；由于当前接口使用 `optional_get_current_user`，未登录场景下 `user_id` 可能为 `None`。
- `file_id` 来源于 `CRUDSession.get_session(db, request.session_id)` 返回会话的 `file_id`。
- `history` 来源于 `get_message_history_as_dicts(db, session.id)`，每条消息只有 `role` 和 `content` 两个字段。
- 上下文截断规则来源于 `getattr(session, "max_context_length", 5) * 2`；当前 `Session` 模型未定义 `max_context_length` 字段，因此默认按 5 轮、10 条消息截断。
- 当前代码会先保存用户消息，再读取历史消息，因此传给 agent 的历史消息应包含本轮用户输入。
- 当前 `CRUDSession.get_session` 只按 `session_id` 查询会话，不校验 `current_user` 归属；后续重构不能直接改变该鉴权行为，若要修正需单独评估接口兼容和安全影响。
- 当前 `get_or_create_chat_session` 会按 `file_id`、`session_id`、`user_id`、`session_type="chat"` 查找聊天会话；当 `current_user` 为空时可能以 `user_id=None` 创建新聊天会话，agent 入参必须兼容 `user_id=None`。
- 当前 backend 不应再向 agent 传递 `model_config`、API key、OpenAI AsyncClient、LLM 实例或模型 SDK 对象；聊天模型选择和密钥读取由 agent 侧负责。

### Step 2.3：文件感知与合同信息抽取入参来源

- √ 核对 `POST /api/contract/upload` 的请求字段：`file`。
- √ 核对 `user_id` 来源：`current_user.id`，由 `optional_get_current_user` 提供且当前未登录会返回 401。
- √ 核对文件名来源：`file.filename`。
- √ 核对文件类型来源：`file.filename` 后缀。
- √ 核对文件保存路径来源：当前保存到 `settings.UPLOAD_DIR/current_user.id/file.filename`。
- √ 核对解析文本来源：当前按文件类型从 `extract_text_from_pdf`、`doc2docx`、`docx2text` 得到 `contract_content`。
- √ 核对合同信息抽取输出来源：当前 LLM 输出经 `parse_contract_info` 解析为 `party_a`、`party_b`、`amount`。
- √ 核对内容文件路径来源：当前将 `contract_content` 写入 `settings.OSS_BUCKET_DIR/<base_name>.txt`，字段为 `contract_content_path`。

#### Step 2.3 核对结论

- 文件感知 agent 完整业务入参字段只能来自现有字段：`user_id`、`filename`、`file_type`、`save_path`。
- `file` 来源于 FastAPI `UploadFile`，当前 backend 会先把文件保存到 `save_path`，再按文件类型解析。
- `user_id` 来源于 `current_user.id`；当前未登录直接返回 401，因此文件感知 agent 不需要兼容 `user_id=None`。
- `filename` 来源于 `file.filename`；当前为空时返回 400。
- `file_type` 来源于 `file.filename` 后缀，当前使用 `file.filename.split('.')[-1].lower()`。
- `save_path` 来源于 `settings.UPLOAD_DIR/current_user.id/file.filename`。
- `contract_content` 当前由 backend 解析得到；后续迁移到 agent 后，应由 agent 返回解析文本或由 agent 写入明确约定的位置，不能凭空构造。
- `party_a`、`party_b`、`amount` 当前由 LLM 输出经 `parse_contract_info` 解析得到；后续由 agent 文件感知或信息抽取能力返回。
- `contract_content_path` 当前由 backend 将 `contract_content` 写入 `settings.OSS_BUCKET_DIR/<base_name>.txt` 后形成，是入库字段，不是 `UploadResponse` 对外字段。
- 当前上传响应字段仍必须保持 `file_id`、`title`、`file_path`、`file_type`、`file_url`、`party_a`、`party_b`、`amount`。
- 当前 backend 不应再向 agent 传递 `llm_client`、API key、OpenAI client、LLM 实例或模型 SDK 对象。

### Step 2.4：agent 返回字段与现有后端消费点

- √ 审阅 agent 返回的风险点字段必须能映射到现有落库字段：`original_content`、`risk_analysis`、`risk_level`、`suggested_content`。
- √ 审阅 agent 返回的失败信息必须能映射到现有 SSE `event="error"`、`data={"message": ...}` 结构。
- √ 审阅完成信息必须由 backend 继续包装为现有 SSE `event="end"` 的 `type`、`summary`、`suggestion` 结构。
- √ 聊天 agent 返回的流式内容必须能映射到现有 `text/event-stream` 数据结构：`type`、`session_id`、`file_id`、`user_id`、`content`、`role`。
- √ 聊天完成信息必须能映射到现有 `type="done"`、`message_id`、`full_content` 结构。
- √ 文件感知 agent 返回的合同信息必须能映射到现有上传入库字段和响应字段：`party_a`、`party_b`、`amount`、`contract_content` 或 `contract_content_path`。

#### Step 2.4 核对结论

- 审阅 agent 返回的单条风险点基础落库字段为 `original_content`、`risk_analysis`、`risk_level`、`suggested_content`，这些字段会被 backend 写入 `CRUDReviewResult.create_review_result`。
- 审阅 agent 的错误输出不能直接改变 SSE 结构，必须由 backend 映射为 `ReviewTaskSSEResponse(event="error", data={"message": ...})`。
- 审阅完成事件当前由 backend 根据风险点数量生成 `summary` 和 `suggestion`，agent 基础重构阶段不需要新增完成摘要字段。
- 聊天 agent 的流式内容应由 backend 映射为 `data: {...}` 格式，其中内容增量字段为 `content`，角色固定为 `assistant`。
- 聊天完成后 backend 仍负责保存 assistant 完整消息，并输出 `type="done"`、`message_id`、`full_content`。
- 聊天错误输出必须映射为现有 `type="error"`、`error` 字段，不能新增错误结构。
- 文件感知 agent 返回的 `party_a`、`party_b`、`amount` 用于入库和 `UploadResponse`。
- 文件感知 agent 返回的 `contract_content` 可由 backend 写入 `contract_content_path`；如果 agent 直接返回 `contract_content_path`，必须确认该路径来自当前共享存储或明确约定的存储边界。
- `contract_content_path` 不属于当前 `UploadResponse` 对外字段，不能作为上传接口新增响应字段。

### Step 2.5：本阶段禁止项

- √ 不设计知识库版本字段。
- √ 不设计 Langfuse trace 字段。
- √ 不设计重向量化字段。
- √ 不设计 API key、model_config、OpenAI client、LLM 实例或模型 SDK 透传字段。
- √ 不修改现有 FastAPI 入参字段、出参字段和 SSE 结构。

#### Step 2.5 核对结论

- Step 2 已限定为当前基础重构，不引入知识库版本、Langfuse trace、重向量化、模型配置透传和 SDK 实例透传。
- Step 2 只确认现有字段来源和映射关系，不定义未来增强字段。
- 后续如果需要新增知识库版本、trace、重向量化等能力，必须放到独立阶段，并明确是否影响接口兼容。
