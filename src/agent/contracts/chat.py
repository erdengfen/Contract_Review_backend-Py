"""Agent 合同聊天契约。

本文件定义 backend 调用 agent 聊天能力时使用的请求和流式响应结构。
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from src.agent.contracts.common import AgentContractModel, ContractFileSnapshot, SessionSnapshot


class ChatMessage(AgentContractModel):
    """聊天消息结构，承接旧版 message 表和 history 字段。"""

    message_id: int | None = Field(None, description="消息ID。")
    session_id: int | None = Field(None, description="消息所属会话ID。")
    role: Literal["user", "assistant"] = Field(..., description="消息角色。")
    content: str | None = Field(None, description="消息内容。")
    parent_id: int | None = Field(None, description="父消息ID。")
    message_index: int | None = Field(None, description="消息顺序索引。")
    created_at: datetime | None = Field(None, description="消息创建时间。")


class ChatRequest(AgentContractModel):
    """聊天请求，承接旧版 ChatRequest、会话、合同和历史消息。"""

    session_id: int | None = Field(None, description="会话ID。")
    user_id: int | None = Field(None, description="用户ID，未登录场景可为空。")
    file_id: int | None = Field(None, description="合同文件ID。")
    content: str | None = Field(None, description="本轮用户输入。")
    parent_id: int | None = Field(None, description="父消息ID。")
    session: SessionSnapshot | None = Field(None, description="会话快照。")
    contract: ContractFileSnapshot | None = Field(None, description="合同文件快照。")
    history: list[ChatMessage] = Field(default_factory=list, description="历史消息。")
    context_window_messages: int = Field(10, description="上下文窗口消息数。")


class ChatResponseChunk(AgentContractModel):
    """聊天流式内容片段。"""

    content: str = Field(..., description="模型输出增量。")
    role: Literal["assistant"] = Field("assistant", description="助手角色。")
    sequence: int | None = Field(None, description="流式片段顺序。")


class ChatDonePayload(AgentContractModel):
    """聊天完成负载，backend 会继续补充旧 SSE 的 message_id。"""

    full_content: str = Field(..., description="完整助手回复。")
    role: Literal["assistant"] = Field("assistant", description="助手角色。")


class ChatErrorPayload(AgentContractModel):
    """聊天错误负载，backend 会映射为旧版 error 字段。"""

    error: str = Field(..., description="错误信息。")
    stage: str | None = Field(None, description="错误阶段。")


def _main_test_chat() -> None:
    """执行聊天契约结构的本文件自检。"""

    message = ChatMessage(role="user", content="请审查付款条款")
    request = ChatRequest(session_id=1, user_id=None, file_id=2, history=[message])
    chunk = ChatResponseChunk(content="存在风险", sequence=1)
    done = ChatDonePayload(full_content="存在风险")
    assert request.user_id is None
    assert request.context_window_messages == 10
    assert chunk.role == "assistant"
    assert done.full_content == "存在风险"


if __name__ == "__main__":
    _main_test_chat()
