# test_deepseek_langchain.py

import os
from langchain_deepseek import ChatDeepSeek  # 来自 langchain-deepseek 集成包
from langchain_core.messages import SystemMessage, HumanMessage

def main():
    api_key = "sk-1df1d558228645848e652205c7a78883"
    if not api_key:
        raise ValueError("请设置环境变量 DEEPSEEK_API_KEY")

    # 实例化 LLM
    llm = ChatDeepSeek(
        model="deepseek-chat",
        api_key=api_key,
        base_url="https://api.deepseek.com/v1",
        temperature=0,
        max_tokens=None,
        timeout=30,
        max_retries=2,
    )

    # 构造消息：系统 + 用户
    messages = [
        SystemMessage(content="You are a helpful assistant."),
        HumanMessage(content="Hello, DeepSeek! Are you available?")
    ]
    response = llm.invoke(messages)
    print("Response:", response.content)

if __name__ == "__main__":
    main()