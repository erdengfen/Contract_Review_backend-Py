"""
LLM初始化模块
"""
from langchain.chat_models import init_chat_model
from .config import DEEPSEEK_API_KEY

def init_llm():
    """初始化LLM"""
    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY环境变量未设置")
    
    return init_chat_model(
        model="deepseek-chat",
        temperature=0,
        model_provider="deepseek",
    )

llm = init_llm()