"""
LLM初始化模块
"""

from langchain_openai import ChatOpenAI
from app.config.config import settings

def init_llm():
    """初始化LLM，支持通过配置切换provider与model"""
    # provider = getattr(settings.openai_config, "provider", "deepseek")
    model = settings.openai_config.model
    api_key = settings.openai_config.api_key
    api_base = settings.openai_config.api_base
    if not api_key:
        raise ValueError("LLM API密钥未设置")
    print(api_key, api_base, model)

    return ChatOpenAI(
        model_name=model,
        openai_api_key=api_key,
        openai_api_base=api_base,
        temperature=0.7,
        max_tokens=512,
    )
