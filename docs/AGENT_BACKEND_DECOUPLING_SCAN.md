# backend 与 agent 解耦扫描记录

本文档记录 Step 1 对当前项目中 LLM、OpenAI SDK、model_config 相关调用点的扫描结果。扫描目标是识别后续需要从 backend 迁移到 agent 或隔离的代码。

## 扫描命令

```bash
rg -n "\binit_llm\b|\bOpenAI\b|\bAsyncClient\b|chat\.completions|stream_chat_model|get_default_model_by_type|model_config|api_key|api_endpoint|model_name|langchain_openai|ChatOpenAI" app main_new.py prompts tests docs -g '*.py' -g '*.md'
rg -n "from openai|import openai|from langchain_openai|init_llm\(|AsyncClient\(|OpenAI\(" app main_new.py -g '*.py'
```

## 必须从 backend 迁移或隔离的调用点

### `app/core/llm.py`

- `app/core/llm.py:5`、`app/core/llm.py:7` 直接导入 `OpenAI` 和 `AsyncClient`。
- `app/core/llm.py:11` 定义 `init_llm`，并在 `app/core/llm.py:26` 创建 `OpenAI` 客户端。
- `app/core/llm.py:44` 定义 `init_chat_model`，并在 `app/core/llm.py:59` 创建 `AsyncClient`。
- `app/core/llm.py:61` 定义 `stream_chat_model`，并在 `app/core/llm.py:73` 直接调用 `chat.completions.create`。
- 迁移方向：移动到 `src/agent/llm/`，backend 不再导入或实例化这些对象。

### `app/core/llm_manager.py`

- `app/core/llm_manager.py:3` 导入 `init_llm`。
- `app/core/llm_manager.py:16` 获取用户 LLM 实例。
- `app/core/llm_manager.py:51` 调用 `init_llm` 并缓存实例。
- `app/core/llm_manager.py:60` 到 `app/core/llm_manager.py:80` 维护用户模型配置和缓存。
- 迁移方向：模型实例缓存应移动到 agent；模型配置管理若仍由 backend 提供界面，不能暴露 SDK 实例给 agent。

### `app/router/chat.py`

- `app/router/chat.py:13` 直接导入 `AsyncClient`。
- `app/router/chat.py:22` 读取默认模型配置。
- `app/router/chat.py:53` 获取默认聊天模型。
- `app/router/chat.py:55` 创建 `AsyncClient`，并把 `model_config` 传给流式生成器。
- 迁移方向：路由只保存用户消息并调用 `src/backend/agent_client/`，由 agent 聊天能力完成模型调用。

### `app/curd/chat.py`

- `app/curd/chat.py:11` 直接导入 `AsyncClient`。
- `app/curd/chat.py:17` 导入 `stream_chat_model`。
- `app/curd/chat.py:96` 的 `chat_stream_generator` 接收 SDK client 和 `model_config`。
- `app/curd/chat.py:113` 调用 `stream_chat_model`。
- 迁移方向：CRUD 层只做消息持久化；模型流式生成迁移到 agent。

### `app/router/contract.py`

- `app/router/contract.py:116` 在上传接口中调用 `llm.init_llm()`。
- `app/router/contract.py:127` 使用 LLM 抽取合同信息。
- 迁移方向：文件上传继续属于 backend；文档解析和合同信息抽取迁移到 agent document_intake 能力。

### `app/router/review_task.py`

- `app/router/review_task.py:31` 导入 `get_default_model_by_type`。
- `app/router/review_task.py:119` 获取默认聊天模型配置。
- `app/router/review_task.py:146` 将 `model_config` 传入 `ContractReviewService.review_contract`。
- 迁移方向：backend 不再读取并传递模型配置；只向 agent 传业务参数，agent 自行解析模型配置和密钥。

### `app/services/contract_review.py`

- `app/services/contract_review.py:14`、`app/services/contract_review.py:22` 导入 `init_llm`。
- `app/services/contract_review.py:38` 初始化 LLM 实例。
- `app/services/contract_review.py:72` 到 `app/services/contract_review.py:84` 执行 RAG 检索。
- `app/services/contract_review.py:90` 到 `app/services/contract_review.py:103` 拼装审阅 prompt。
- `app/services/contract_review.py:105` 调用 `self.llm.chat.completions.create`。
- 迁移方向：整体迁移到 `src/agent/review/`、`src/agent/rag/` 和 `src/agent/llm/`。

### `app/schemas/contract_file.py`

- `app/schemas/contract_file.py:10` 从 `openai` 导入 `BaseModel`。
- 迁移方向：这是 schema 层对 OpenAI SDK 的不必要依赖，后续应改为 `pydantic.BaseModel`；本次不改接口字段。

## agent 或实验区调用点

### `app/rag/clients/embedding_remote.py`

- `app/rag/clients/embedding_remote.py:37` 动态导入 `OpenAI`。
- `app/rag/clients/embedding_remote.py:42` 创建远程 embedding 客户端。
- 迁移方向：RAG 客户端后续归入 agent；不应被 backend 直接依赖。

### `app/services/multi_agent/config.py`

- `app/services/multi_agent/config.py:9` 导入 `OpenAI`。
- `app/services/multi_agent/config.py:98` 定义 demo LLM 初始化函数。
- `app/services/multi_agent/config.py:107` 创建 OpenAI 客户端。
- 迁移方向：该目录当前仍是实验区；后续迁移时只保留可复用设计，不直接接入生产 backend。

## 模型配置管理相关调用点

### `app/router/model_configs.py` 与 `app/curd/model_configs.py`

- 当前负责模型配置的创建、更新、查询、默认模型读取和删除。
- 后续需要明确模型配置的所有权：如果 agent 独立服务需要读取密钥，应由 agent 的数据库访问边界读取，而不是由 backend 查询后透传。

### `app/router/llm_config.py`

- 当前负责用户级 LLM 配置管理，并通过 `llm_manager` 清理缓存或切换 active model。
- 后续需要评估是否保留在 backend 管理界面，或迁移到 agent 管理域。

## Step 1 结论

- 当前 backend 与 agent 相关能力耦合较高，LLM SDK 实例化、模型配置读取、prompt 拼装、RAG 和流式输出分布在 router、curd、core 和 services 中。
- 第一阶段不能直接删除旧逻辑；应先通过 `src/backend/agent_client/` 与 `src/agent/api/` 建立调用边界。
- 后续迁移时，backend 对 agent 的调用入参必须限定为业务身份和上下文参数，不能传递密钥、SDK client 或模型实例。
