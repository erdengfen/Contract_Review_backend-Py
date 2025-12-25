import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from httpx import Client
from app.config.config import settings

import pytest

@pytest.mark.asyncio
async def test_deepseek_async():
    print("开始异步测试 DeepSeek Chat 接口连接...\n")

    model = settings.openai_config.model
    api_key = settings.openai_config.api_key
    api_base = settings.openai_config.api_base
    if not api_key:
        raise ValueError("LLM API密钥未设置")
    print(api_key, api_base, model)

    http_client = Client(timeout=30.0)

    client = ChatOpenAI(
        model_name=model,
        openai_api_key=api_key,
        openai_api_base=api_base,
        temperature=0.7,
        max_tokens=512,
        http_client=http_client,
        timeout=30.0,
    )

    try:
        # 直接调用 invoke（异步）
        resp = await client.ainvoke(
            [
                SystemMessage(content="你是一个测试引擎，只需要正确返回 JSON。"),
                HumanMessage(content="测试一下，请回复：\"OK\""),
            ]
        )

        print("接口返回结果：")
        print(resp)
        print("\n解析后的内容：", resp.content)

    except Exception as e:
        print("\n❌ 接口调用失败！错误：", e)


if __name__ == "__main__":
    asyncio.run(test_deepseek_async())
