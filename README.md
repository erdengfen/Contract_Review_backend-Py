# 合同智能审阅后端服务

面向高校及企事业单位合同管理场景的 AI 合同审阅后端服务。系统采用“看板 + 应用功能 + 文本处理 + AI 能力 + 规则引擎 + 大模型接入”的全链路架构，支撑合同文件上传、文本解析、合同审阅、合同比对、合同问答、风险点处理、模型配置、提示词管理和看板统计。

## 核心能力

- 合同文件上传、保存、下载与结构化信息抽取。
- 合同审阅任务启动、流式风险点输出、风险点采纳与合同修订状态维护。
- 合同比对任务启动、段落级与字符级差异结果输出。
- 基于会话的合同聊天与上下文消息管理。
- 合同类型、系统 Prompt、机构 Prompt、个性化 Prompt 管理。
- 模型配置管理，支持按模型类型维护默认模型。
- 看板统计接口，沉淀合同审阅数量、风险修订、合同类型与趋势数据。
- CAS 与账号密码登录，使用 JWT access token 与 refresh token 管理会话。

## 技术栈

- 语言与运行时：Python 3.11.x。
- 包管理：uv，依赖唯一来源为 `pyproject.toml`，锁文件为 `uv.lock`。
- Web 框架：FastAPI、Uvicorn。
- 数据校验：Pydantic v2。
- 数据库：MySQL + SQLAlchemy + PyMySQL。
- 缓存与令牌状态：Redis。
- 流式输出：SSE / `text/event-stream`。
- 文档解析：MinerU、Docling、Python-docx、DeepSeek OCR、PyMuPDF、pdfplumber、pdf2docx、pdf2image、pytesseract、LibreOffice。
- LLM 调用：OpenAI-compatible API、LangChain Core、LangChain OpenAI。
- RAG 与向量检索：Qdrant、sentence-transformers、混合检索、多路召回、rerank 服务。
- Agent 编排：LangGraph Router、Specialist 并行审阅、Gate 检查、Arbitration 仲裁。
- 观测追踪：Langfuse 全链路追踪。
- 规则引擎：中央法规、地方法规、教委文件、学校规则、部门规章、规则 Skills。

## 目录结构

```text
.
├── app/
│   ├── config/          # 配置加载与 config.yaml
│   ├── core/            # 全局初始化、数据库、依赖、LLM 基础能力
│   ├── curd/            # 数据访问层
│   ├── middlewares/     # 鉴权中间件
│   ├── models/          # SQLAlchemy 模型
│   ├── rag/             # RAG 配置、检索与启动检查
│   ├── router/          # FastAPI 路由
│   ├── schemas/         # Pydantic 请求与响应模型
│   ├── services/        # 合同审阅、合同比对、多 Agent 实验链路
│   └── utils/           # 文档解析、MCP、切片等工具
├── prompts/             # Prompt 模板与变量
├── tests/               # 测试与联调脚本
├── graph.md             # 项目全链路架构图
├── main_new.py          # FastAPI 应用入口
├── pyproject.toml       # 项目依赖唯一来源
└── uv.lock              # uv 锁文件
```

## 环境要求

- Python：3.11.x，当前 `.python-version` 为 `3.11.11`。
- uv：用于安装依赖、运行服务、运行脚本和测试。
- MySQL：存储用户、合同、会话、审阅任务、模型配置等业务数据。
- Redis：存储登录令牌、并发登录锁和相关缓存状态。
- Qdrant：RAG 向量检索服务。
- 可选系统依赖：LibreOffice、OCR 相关依赖、PDF 解析依赖。

## 配置说明

默认配置文件为 `app/config/config.yaml`，并支持通过环境变量覆盖部分 AI 与 RAG 配置。敏感信息不应写入 README、日志或调试输出。

常用环境变量：

| 变量 | 说明 |
| --- | --- |
| `OPENAI_API_KEY` | OpenAI-compatible LLM API Key |
| `OPENAI_API_BASE` | LLM API 基础地址 |
| `OPENAI_MODEL` | 默认 LLM 模型名称 |
| `RAG_EMBEDDING_PROVIDER_MODE` | Embedding 提供方式，`local` 或 `remote` |
| `RAG_EMBEDDING_REMOTE_MODEL` | 远程 Embedding 模型名称 |
| `RAG_EMBEDDING_REMOTE_BASE_URL` | 远程 Embedding 服务地址 |
| `RAG_EMBEDDING_REMOTE_API_KEY` | 远程 Embedding API Key |
| `RAG_RERANK_REMOTE_MODEL` | 远程 rerank 模型名称 |
| `RAG_RERANK_REMOTE_BASE_URL` | 远程 rerank 服务地址 |
| `RAG_RERANK_REMOTE_API_KEY` | 远程 rerank API Key |
| `RAG_STARTUP_ENABLED` | 是否启用 RAG 启动检查 |
| `RAG_STARTUP_ENSURE_QDRANT_COLLECTIONS` | 启动时是否检查并补齐 Qdrant collection |
| `RAG_STARTUP_FAIL_FAST` | RAG 启动检查失败时是否中断服务 |

## 部署与启动

### 1. 安装依赖

```bash
uv sync
```

### 2. 启动 Qdrant

```bash
docker compose -f docker-compose.qdrant.yml up -d
```

如使用远程 Qdrant，可在配置中调整 `rag_config.qdrant` 相关地址与端口。

### 3. 准备 MySQL 与 Redis

确认 `app/config/config.yaml` 中的 MySQL、Redis、JWT、CAS、MCP、LLM 与 RAG 配置可用。首次部署需要准备数据库表结构和基础数据，至少包括用户、合同类型、默认模型配置、Prompt 配置等业务基础记录。

### 4. 启动后端服务

项目统一使用 uv 启动：

```bash
uv run uvicorn main_new:app --host 0.0.0.0 --port 8080
```

启动后可访问：

- Swagger 文档：`http://localhost:8080/docs`
- ReDoc 文档：`http://localhost:8080/redoc`
- OpenAPI JSON：`http://localhost:8080/openapi.json`

### 5. 运行测试

```bash
uv run pytest
```

## 接口约定

### 统一响应结构

除文件下载和流式接口外，大部分接口返回 `GenericResponse`：

```json
{
  "code": 200,
  "msg": "success",
  "data": {}
}
```

### 鉴权

大部分业务接口需要登录态。登录后在请求头中携带：

```http
Authorization: Bearer <access_token>
```

认证失败时返回业务错误码或 HTTP 401，具体行为由全局鉴权中间件和路由内鉴权共同决定。

### 流式接口

合同审阅与合同聊天使用 SSE 或流式响应：

- 审阅任务：`POST /api/review_task/start_task`，返回 `text/event-stream`。
- 合同聊天：`POST /api/chat/chat`，返回 `text/event-stream`。

审阅任务事件结构：

```json
{
  "event": "message",
  "data": {
    "index": 1,
    "original_content": "原条款",
    "risk_analysis": "风险分析",
    "risk_level": "风险等级",
    "suggested_content": "建议修改内容"
  }
}
```

任务结束事件：

```json
{
  "event": "end",
  "data": {
    "type": "summary",
    "summary": "审阅摘要",
    "suggestion": "处理建议"
  }
}
```

## API 详情

### 用户管理 `/api/user`

| 方法 | 路径 | 说明 | 请求参数 | 响应 |
| --- | --- | --- | --- | --- |
| `POST` | `/api/user/create` | 创建用户 | `username`, `password` | 用户信息 |
| `GET` | `/api/user/get_user/{user_id}` | 根据 ID 查询用户 | `user_id` | 用户信息 |
| `GET` | `/api/user/me` | 获取当前登录用户信息 | `Authorization` | 当前用户 |
| `GET` | `/api/user/all` | 获取所有活跃用户 | 无 | 用户列表 |
| `PUT` | `/api/user/update/{user_id}` | 更新用户信息 | `user_id`, `username`, `password` | 用户信息 |
| `POST` | `/api/user/disable/{user_id}` | 禁用用户 | `user_id` | 操作结果 |
| `POST` | `/api/user/login` | 用户登录 | `identifier`, `password` | `access_token`, `refresh_token` |
| `POST` | `/api/user/refresh` | 刷新 access token | `refresh_token` | 新 access token |
| `POST` | `/api/user/logout` | 用户登出 | `Authorization` | 操作结果 |
| `GET` | `/api/user/cas_login` | CAS 登录跳转 | 无 | 重定向 |
| `GET` | `/api/user/cas_callback` | CAS 登录回调 | `ticket` | 重定向或令牌 |

### CAS 认证

| 方法 | 路径 | 说明 | 请求参数 | 响应 |
| --- | --- | --- | --- | --- |
| `GET` | `/login` | CAS 登录入口 | 无 | 重定向 |
| `GET` | `/logout/` | CAS 登出 | `Authorization` 或 `token` | 操作结果 |
| `GET` | `/cas_callback` | CAS 回调 | `ticket` | 登录结果 |

### 会话管理 `/api/session`

| 方法 | 路径 | 说明 | 请求参数 | 响应 |
| --- | --- | --- | --- | --- |
| `POST` | `/api/session/create_session` | 创建会话 | `title`, `session_type`, `file_id` | 会话信息 |
| `POST` | `/api/session/list_sessions` | 获取用户会话列表 | `page`, `page_size`, `session_type` | 审阅或比对会话列表 |
| `POST` | `/api/session/update_session_title` | 修改会话标题 | `session_id`, `new_title` | 会话信息 |
| `POST` | `/api/session/delete_session` | 删除会话 | `session_id` | `true` |
| `POST` | `/api/session/session_history_detail` | 获取会话历史 | `session_id` | 聊天消息、审阅结果或比对结果 |

`session_type` 当前主要使用 `chat`、`review`、`compare`。

### 文件上传下载 `/api/contract`

| 方法 | 路径 | 说明 | 请求参数 | 响应 |
| --- | --- | --- | --- | --- |
| `POST` | `/api/contract/upload` | 上传并解析合同文件 | `multipart/form-data: file` | 文件 ID、标题、路径、类型、访问 URL、甲乙方、金额 |
| `POST` | `/api/contract/save_file` | 仅保存合同文件 | `multipart/form-data: file` | 文件记录 |
| `POST` | `/api/contract/set_contract_type` | 设置合同类型与审查立场 | `file_id`, `contract_type_id`, `review_position` | 操作结果 |
| `GET` | `/api/contract/download/{file_id}` | 下载合同文件 | `file_id` | 文件流 |
| `DELETE` | `/api/contract/{file_id}` | 删除合同文件 | `file_id` | 操作结果 |

### 合同审阅 `/api/review_task`

| 方法 | 路径 | 说明 | 请求参数 | 响应 |
| --- | --- | --- | --- | --- |
| `POST` | `/api/review_task/start_task` | 启动审阅任务 | `session_id`, `stance`, `intensity`, `description`, `contract_type`, `max_concurrent` | SSE 风险点事件 |
| `POST` | `/api/review_task/accept_risk_point` | 接受或取消接受风险点修订 | `session_id`, `task_id`, `index`, `is_accepted` | 操作结果 |
| `POST` | `/api/review_task/accept_contract_file` | 修改合同修订状态 | `file_id`, `is_accepted` | 操作结果 |

审阅任务会读取会话关联的已解析合同文本，按分块并发调用审阅模型，并按原分块顺序输出风险点。

### 合同比对 `/api/comparison_task`

| 方法 | 路径 | 说明 | 请求参数 | 响应 |
| --- | --- | --- | --- | --- |
| `POST` | `/api/comparison_task/start` | 启动合同比对任务 | `standard_file_id`, `comparison_file_id`, `session_id`, `title` | 比对任务 ID、会话 ID、差异摘要、差异详情、文件信息 |

当前比对接口仅支持 `docx` 文件。输出包含段落级差异和字符级差异详情。

### 合同聊天 `/api/chat`

| 方法 | 路径 | 说明 | 请求参数 | 响应 |
| --- | --- | --- | --- | --- |
| `POST` | `/api/chat/chat` | 围绕合同会话进行聊天 | `session_id`, `content`, `parent_id` | SSE 流式回答 |

聊天接口会读取会话消息历史，并使用默认 `chat` 模型配置生成流式回答。

### 合同类型管理 `/api/contract_type`

| 方法 | 路径 | 说明 | 请求参数 | 响应 |
| --- | --- | --- | --- | --- |
| `GET` | `/api/contract_type/detail/{contract_type_id}` | 查询合同类型详情 | `contract_type_id` | 合同类型 |
| `GET` | `/api/contract_type/contract_type_list` | 查询合同类型列表 | 无 | 合同类型列表 |
| `POST` | `/api/contract_type/create_contract_type` | 创建合同类型 | `name`, `description` | 合同类型 |
| `POST` | `/api/contract_type/update_contract_type` | 更新合同类型 | `contract_type_id`, `name`, `description` | 合同类型 |
| `POST` | `/api/contract_type/activate_contract_type` | 激活或停用合同类型 | `contract_type_id`, `is_active` | 合同类型 |

### Prompt 管理 `/api/prompt_manage`

| 方法 | 路径 | 说明 | 请求参数 | 响应 |
| --- | --- | --- | --- | --- |
| `POST` | `/api/prompt_manage/create_system` | 创建系统 Prompt | `contract_type_id`, `prompt_name`, `prompt_content` | 系统 Prompt |
| `POST` | `/api/prompt_manage/get_system_prompt_id` | 按合同类型获取系统 Prompt | `contract_type_id` | 系统 Prompt |
| `POST` | `/api/prompt_manage/system_update` | 更新系统 Prompt | `id`, `prompt_name`, `prompt_content` | 系统 Prompt |
| `GET` | `/api/prompt_manage/system_list` | 获取系统 Prompt 列表 | 无 | 系统 Prompt 列表 |
| `GET` | `/api/prompt_manage/org` | 获取机构 Prompt | `contract_type_id`, `organization_id` | 机构 Prompt |
| `POST` | `/api/prompt_manage/org_update` | 更新机构 Prompt | `base_prompt_id`, `organization_id`, `prompt_name`, `prompt_text` | 机构 Prompt |
| `POST` | `/api/prompt_manage/org_restore` | 恢复机构 Prompt | `base_prompt_id`, `organization_id` | 机构 Prompt |
| `POST` | `/api/prompt_manage/override` | 创建个性化 Prompt | `base_prompt_id`, `override_name`, `override_text` | 个性化 Prompt |
| `POST` | `/api/prompt_manage/override/update` | 更新个性化 Prompt | `id`, `override_name`, `override_text` | 个性化 Prompt |
| `POST` | `/api/prompt_manage/override/delete` | 删除个性化 Prompt | `prompt_id` | 删除结果 |

### 模型配置管理 `/api/model_configs`

| 方法 | 路径 | 说明 | 请求参数 | 响应 |
| --- | --- | --- | --- | --- |
| `POST` | `/api/model_configs/create_model/` | 创建模型配置 | 模型名称、类型、提供方、API 地址、API Key、temperature、top_p、max_tokens 等 | 模型配置 |
| `POST` | `/api/model_configs/update_model/{model_id}` | 更新模型配置 | `model_id` 与模型配置字段 | 模型配置 |
| `GET` | `/api/model_configs/get_default_model/{model_type}` | 获取指定类型默认模型 | `model_type` | 模型配置 |
| `GET` | `/api/model_configs/get_all_models/` | 获取模型配置列表 | `page`, `size` | 模型配置列表 |
| `GET` | `/api/model_configs/get_model_by_id/{model_id}` | 按 ID 获取模型配置 | `model_id` | 模型配置 |
| `POST` | `/api/model_configs/delete_model/{model_id}` | 删除模型配置 | `model_id` | 操作结果 |

### 看板管理 `/api/signboard`

| 方法 | 路径 | 说明 | 请求参数 | 响应 |
| --- | --- | --- | --- | --- |
| `GET` | `/api/signboard/statistics_overview` | 获取合同审阅概览 | 无 | 审阅数量、部门数、用户数、服务师生数、累计金额 |
| `GET` | `/api/signboard/statistics_revisions` | 获取修订风险点与错误点 | 无 | 风险点修订数、错误点修订数 |
| `GET` | `/api/signboard/statistics_contract-types` | 获取合同类型统计 | 无 | 合同类型数量、使用单位、用户数、分类数量 |
| `POST` | `/api/signboard/get_contract_count` | 获取指定合同类型统计 | `contract_type_id` | 合同类型统计 |
| `GET` | `/api/signboard/trends_contracts` | 获取合同审阅趋势 | `period`, `contract_type_ids`, `start_date`, `end_date` | 趋势列表 |

## 典型业务流程

### 合同审阅

1. 调用 `/api/user/login` 获取令牌。
2. 调用 `/api/contract/upload` 上传并解析合同。
3. 调用 `/api/session/create_session` 创建 `review` 会话并关联 `file_id`。
4. 调用 `/api/review_task/start_task` 启动审阅任务，消费 SSE 风险点事件。
5. 调用 `/api/review_task/accept_risk_point` 或 `/api/review_task/accept_contract_file` 处理审阅结果。
6. 调用 `/api/session/session_history_detail` 查询审阅历史。

### 合同比对

1. 调用 `/api/contract/save_file` 保存两个 `docx` 文件。
2. 调用 `/api/comparison_task/start` 传入 `standard_file_id` 与 `comparison_file_id`。
3. 接收差异摘要、段落级差异和字符级差异。
4. 调用 `/api/session/session_history_detail` 查询比对历史。

### 合同聊天

1. 调用 `/api/session/create_session` 创建 `chat` 会话并关联合同文件。
2. 调用 `/api/chat/chat` 发送问题。
3. 消费 `text/event-stream` 流式回答。

## 开发规范

- 依赖只维护在 `pyproject.toml`，新增依赖后使用 uv 重新生成并提交 `uv.lock`。
- 运行脚本使用 `uv run python <script>.py`。
- 运行测试使用 `uv run pytest`。
- 修改 `app/services/` 中 prompt、模型参数、输出解析、缓存键、调用协议时视为高风险，需要保持输出格式兼容并保留失败兜底。
- 禁止在日志、测试样例和调试输出中泄露合同原文、OCR 全文、客户敏感信息、token 或密钥。
- 修改公共函数签名、返回结构、配置字段时，需要检查全部调用方。
