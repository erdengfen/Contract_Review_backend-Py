"""
LLM初始化模块
"""
from langchain.chat_models import init_chat_model

def init_llm(api_key: str, model: str, base_url: str = None, model_provider: str = "deepseek"):
    """
    初始化 LLM 客户端（支持不同模型与 API key）
    """
    if not api_key:
        raise ValueError("api_key 未设置")

    # 初始化模型
    return init_chat_model(
        model=model,
        temperature=0,
        model_provider=model_provider,
        base_url=base_url,
        api_key=api_key
    )