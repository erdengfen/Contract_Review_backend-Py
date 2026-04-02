"""
review_contract 端到端验证入口。
"""
from __future__ import annotations

import argparse
import asyncio
from types import SimpleNamespace

from app.config.config import settings
from app.rag.factory import build_rag_service
from app.services.contract_review import ContractReviewService


class _CapturingFakeChatCompletions:
    def __init__(self):
        self.last_messages = []

    def create(self, *, model: str, messages: list, tools: list):
        self.last_messages = messages
        fake_review_result = """
【修改点1】付款条款表述不清
【原文】甲方应在项目完成后付款。
【风险分析】付款触发条件和付款时间不明确，容易引发履约争议。
【风险等级】中
【修改后的内容】甲方应在乙方完成项目并经甲方书面验收通过后10个工作日内付款。
【修改理由】补足验收条件和付款期限，减少争议。
【风险类型】付款条款

【修改点2】违约责任偏弱
【原文】任何一方违约应承担责任。
【风险分析】违约责任未量化，实际追责时缺乏执行标准。
【风险等级】高
【修改后的内容】任何一方违约的，应承担守约方全部损失，并按合同总金额的10%支付违约金。
【修改理由】明确违约后果，提高约束力。
【风险类型】违约责任
""".strip()
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=fake_review_result))]
        )


class _CapturingFakeLLM:
    def __init__(self):
        self.completions = _CapturingFakeChatCompletions()
        self.chat = SimpleNamespace(completions=self.completions)


async def run_review_contract_validation() -> dict:
    fake_llm = _CapturingFakeLLM()
    rag_service = build_rag_service(settings.rag_config)

    service = ContractReviewService.__new__(ContractReviewService)
    service.llm = fake_llm
    service.mcp_client = None
    service.rag_service = rag_service

    result = await service.review_contract(
        model_config=SimpleNamespace(model_name="fake-contract-review-model"),
        chunk_text="合同格式条款提供方减轻自身责任，且付款条件不明确，违约责任未量化。",
        stance="甲方",
        intensity="标准",
        context="这是第 1 个分块，共 1 个。",
        contract_type="服务合同",
    )

    user_prompt = fake_llm.completions.last_messages[1]["content"]
    return {
        "result": result,
        "user_prompt": user_prompt,
    }


async def _main_test_review_contract_validation():
    payload = await run_review_contract_validation()
    result = payload["result"]
    user_prompt = payload["user_prompt"]

    assert len(result) == 2
    assert "## 外部法律依据" in user_prompt
    assert "## 内部审阅规则" in user_prompt
    assert "中华人民共和国民法典" in user_prompt or "重庆市合同监督条例（示例）" in user_prompt
    assert "付款条款审阅规则" in user_prompt or "违约责任规则" in user_prompt
    assert result[0]["risk_level"] == "中"
    assert result[1]["risk_level"] == "高"
    print("review_contract validation self test passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="review_contract 端到端验证入口")
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="执行端到端验证并断言 RAG 上下文已注入 review_contract。",
    )
    args = parser.parse_args()

    if args.self_test:
        asyncio.run(_main_test_review_contract_validation())
    else:
        asyncio.run(_main_test_review_contract_validation())
