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
#from langchain.chat_models import init_chat_model
#
# def init_llm(api_key: str, model: str, base_url: str = None, model_provider: str = "deepseek"):
#     """
#     初始化 LLM 客户端（支持不同模型与 API key）
#     """
#     if not api_key:
#         raise ValueError("api_key 未设置")
#
#     # 初始化模型
#     return init_chat_model(
#         model=model,
#         temperature=0,
#         model_provider=model_provider,
#         base_url=base_url,
#         api_key=api_key
#     )