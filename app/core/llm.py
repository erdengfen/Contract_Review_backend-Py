"""
LLM初始化模块
"""
import os
from langchain.chat_models import init_chat_model
from app.config.config import settings

def init_llm():
    """初始化LLM，支持通过配置切换provider与model"""
    provider = getattr(settings.openai_config, "provider", "deepseek")
    model = settings.openai_config.model
    api_key = settings.openai_config.api_key

    if not api_key:
        raise ValueError("LLM API密钥未设置")

    if provider == "deepseek":
        os.environ["DEEPSEEK_API_KEY"] = api_key
    elif provider == "openai":
        os.environ["OPENAI_API_KEY"] = api_key
    else:
        # 其他provider按需扩展，默认写入通用OPENAI_API_KEY以兼容部分适配器
        os.environ["OPENAI_API_KEY"] = api_key

    return init_chat_model(
        model=model,
        temperature=0,
        model_provider=provider,
    )
