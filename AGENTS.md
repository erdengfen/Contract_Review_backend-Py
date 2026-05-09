# AGENTS.md

## 最高优先级约束
- 所有 FastAPI 接口的数据字段，即当前已存在的后端接口入参字段与出参字段，禁止做任何更改。
- 旧版本业务逻辑依赖 `app/` 下现有实现，新版本重构在 `src/` 下开发；`docs/LEGACY_AGENT_FIELD_BASELINE.md` 记录的均为旧版本字段详情，重构过程中必须参照该文档进行 agent 与 backend 的字段设计。

## Scope
- 本文件适用于整个仓库。
- 当前协作重点是 `app/services/` 中的 agent / LLM 调用链路；无明确任务时，不要扩展到其他后端模块。

## 文档读取策略
- 进入开发任务时，先读本文件确认项目边界和执行约束，再按任务类型读取对应文档。
- 涉及测试与验收标准，读 `docs/TESTING.md`。
- 涉及代码编写、修改、重构，必须读 `docs/CODE_STYLE.md`。
- 涉及 agent、backend 解耦或能力接口字段设计，必须读 `docs/LEGACY_AGENT_FIELD_BASELINE.md`。
- 涉及分步开发长任务，必须更新 `PLANS.md`。

## Environment
- 必须使用 `uv` 管理和运行项目。
- 必须以 `pyproject.toml` 为唯一依赖源。
- 必须提交并维护 `uv.lock`；禁止手工编辑锁文件。
- `requirements.txt` 仅允许临时保留；禁止再把它当作安装入口或手工维护。
- Python 版本必须使用 `3.11.x`，并以 `.python-version` 与 `pyproject.toml` 为准。

## Commands
- 启动服务必须使用：`uv run uvicorn main_new:app --host 0.0.0.0 --port 8080`
- 运行脚本必须使用：`uv run python <script>.py`
- 运行测试必须使用：`uv run pytest`
- 新增依赖后，必须重新生成锁文件并执行最小验证。

## Change Boundaries
- 禁止无关重构。
- 所有注释和描述文本使用中文
- 禁止大范围重命名、批量格式化、目录搬迁。
- 未经明确要求，不要修改 `app/router/`、`app/models/`、鉴权、中间件、数据库结构、Docker 与部署脚本。
- 修改公共函数签名、返回结构、配置字段时，必须检查全部调用方。

## Agent And LLM Rules
- `app/services/` 中涉及 prompt、模型参数、输出解析、缓存键、调用协议的修改默认视为高风险。
- 禁止随意改动模型名称、temperature、top_p、max_tokens、SSE 输出结构，除非任务明确要求。
- 修改 prompt 拼装逻辑时，必须保持现有输出格式兼容；若有破坏性变化，必须明确说明。
- 修改 LLM 输出解析逻辑时，必须保留失败兜底，避免因模型输出抖动直接中断流程。
- 禁止在未读懂现有约定前改动风险等级、风险标签、合同分类、修改点字段语义。
- 禁止随意改动分块逻辑、并发控制、结果落库顺序、缓存键格式。

## Sensitive Data
- 禁止在日志、测试样例、调试输出中泄露合同原文、OCR 全文、客户敏感信息、token、密钥。
- 发现现有代码输出敏感信息时，不要扩散到新代码。

## Validation
- 完成任务前，必须执行与改动直接相关的最小验证。
- AI 相关改动优先做结构验证，避免依赖具体自然语言措辞的脆弱断言。
- 若因外部服务、密钥、数据库、Redis、MCP 不可用而无法完成验证，必须明确说明未验证边界。

## Final Report
- 每次任务结束必须说明：
- 本次改动内容
- 未改动但相关的部分
- 风险点
- 验证结果
- 后续建议
