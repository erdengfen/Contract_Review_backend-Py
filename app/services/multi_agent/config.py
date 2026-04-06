"""multi_agent 目录独立配置。"""

from __future__ import annotations

import os
from functools import lru_cache

from openai import OpenAI
from pydantic import BaseModel, Field

from app.config.config import settings


def _read_env(name: str, default):
    value = os.getenv(name)
    if value in {None, ""}:
        return default
    return value


class MultiAgentDemoModelConfig(BaseModel):
    """multi_agent demo 专用模型配置。"""

    model_name: str = Field(
        default_factory=lambda: _read_env(
            "MULTI_AGENT_DEMO_MODEL_NAME",
            settings.openai_config.model,
        ),
        description="demo 使用的模型名称",
    )
    api_key: str = Field(
        default_factory=lambda: _read_env(
            "MULTI_AGENT_DEMO_API_KEY",
            settings.openai_config.api_key,
        ),
        description="demo 使用的 API Key",
    )
    api_base: str = Field(
        default_factory=lambda: _read_env(
            "MULTI_AGENT_DEMO_API_BASE",
            settings.openai_config.api_base,
        ),
        description="demo 使用的 API Base",
    )
    temperature: float = Field(
        default_factory=lambda: float(_read_env("MULTI_AGENT_DEMO_TEMPERATURE", "0.2")),
        description="demo 使用的温度参数",
    )
    top_p: float = Field(
        default_factory=lambda: float(_read_env("MULTI_AGENT_DEMO_TOP_P", "0.95")),
        description="demo 使用的 top_p 参数",
    )
    max_tokens: int = Field(
        default_factory=lambda: int(_read_env("MULTI_AGENT_DEMO_MAX_TOKENS", "2048")),
        description="demo 使用的最大输出长度",
    )


class MultiAgentDemoConfig(BaseModel):
    """multi_agent demo 运行配置。"""

    model: MultiAgentDemoModelConfig = Field(
        default_factory=MultiAgentDemoModelConfig,
        description="demo 专用模型配置",
    )
    chunk_size: int = Field(default=4000, description="分块长度")
    max_concurrent_reviews: int = Field(default=3, description="最大并发审阅数")
    default_stance: str = Field(default="甲方", description="默认审阅立场")
    default_intensity: str = Field(default="标准", description="默认审阅强度")
    default_contract_type: str = Field(default="通用", description="默认合同类型")


@lru_cache(maxsize=1)
def get_multi_agent_demo_config() -> MultiAgentDemoConfig:
    """返回 multi_agent demo 配置。"""
    return MultiAgentDemoConfig()


def init_multi_agent_demo_llm(
    model_config: MultiAgentDemoModelConfig | None = None,
) -> OpenAI:
    """初始化 multi_agent demo 专用 LLM 客户端。"""
    config = model_config or get_multi_agent_demo_config().model
    if not config.api_key:
        raise ValueError("multi_agent demo API Key 未设置")
    if not config.api_base:
        raise ValueError("multi_agent demo API Base 未设置")
    return OpenAI(
        api_key=config.api_key,
        base_url=config.api_base,
    )
