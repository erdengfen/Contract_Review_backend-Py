"""
LLM初始化模块
"""
from aiohttp.log import client_logger
from openai import OpenAI
from app.config.config import settings
from openai import AsyncClient
from app.schemas.model_configs import ModelConfigResponse


def init_llm() -> OpenAI:
    """
    初始化LLM，model字段在调用时传入
    :return:
    """
    # provider = getattr(settings.openai_config, "provider", "deepseek")
    # model = settings.openai_config.model
    api_key = settings.openai_config.api_key
    api_base = settings.openai_config.api_base
    if not api_key:
        raise ValueError("LLM API密钥未设置")
    if not api_base:
        raise ValueError("BASE_URL未设置")
    # print(api_key, api_base, model)

    client = OpenAI(
        api_key=api_key,
        base_url=api_base,
    )

    return client

    # return ChatOpenAI(
    #     model_name=model,
    #     openai_api_key=api_key,
    #     openai_api_base=api_base,
    #     temperature=0.7,
    #     max_tokens=512,
    #     timeout=15.0,
    #     # http_client=http_client,
    # )
# ----------------------------------
# 以下为保留方法
def init_chat_model(
        api_key: str,
        api_base: str

):
    """
    初始化聊天模型
    :param api_key: OpenAI API密钥
    :param api_base: OpenAI API基础URL
    :param model: 模型名称
    :param temperature: 温度参数，控制生成文本的随机性
    :param max_tokens: 最大令牌数，限制生成文本的长度
    :return: 初始化后的ChatOpenAI模型实例
    """
    """初始化聊天模型"""
    return AsyncClient(api_key=api_key, base_url=api_base)

async def stream_chat_model(
        async_client: AsyncClient,
        messages: list,
        model_config: ModelConfigResponse,
):
    """
    流式聊天模型
    :param async_client: 初始化后的AsyncClient模型实例
    :param messages: 消息列表，包含用户和助手的交互记录
    :param model_config: 模型配置，包含温度、Top P、存在惩罚、频率惩罚、最大令牌数等参数
    :return: 流式响应生成器，每次返回一个令牌
    """
    response = await async_client.chat.completions.create(
        model=model_config.model_name,
        stream=True,
        messages=messages,
        temperature=model_config.temperature,
        top_p=model_config.top_p,
        presence_penalty=model_config.presence_penalty,
        frequency_penalty=model_config.frequency_penalty,
        max_tokens=model_config.max_tokens,
    )
    async for chunk in response:
        if chunk.choices and chunk.choices[0].delta.content:
            delta = chunk.choices[0].delta.content or ""
            yield delta
        else:
            continue

