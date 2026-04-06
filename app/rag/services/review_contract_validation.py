"""
review_contract 脱库联调与健康检查入口。
"""
from __future__ import annotations

import argparse
import asyncio
from types import SimpleNamespace
from typing import Any

from app.config.config import settings
from app.rag.schemas import RetrievalResponse
from app.services.contract_review import ContractReviewService


DEFAULT_CHUNK_TEXT = "合同格式条款提供方减轻自身责任，且付款条件不明确，违约责任未量化。"


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


class _StaticFakeRagService:
    def retrieve_for_review(self, request) -> RetrievalResponse:
        return RetrievalResponse(
            prompt_context=(
                "## 外部法律依据\n"
                "1. 中华人民共和国民法典 第五百零九条\n"
                "   来源类型：law\n"
                "   内容：当事人应当按照约定全面履行自己的义务。\n\n"
                "## 内部审阅规则\n"
                "1. 付款条款审阅规则（review_rule）\n"
                "   规则ID：rule-1\n"
                "   内容：付款条款应明确验收条件、付款期限和发票要求。"
            )
        )


def _build_service_for_self_test() -> tuple[ContractReviewService, _CapturingFakeLLM]:
    fake_llm = _CapturingFakeLLM()
    service = ContractReviewService.__new__(ContractReviewService)
    service.llm = fake_llm
    service.mcp_client = None
    service.rag_service = _StaticFakeRagService()
    return service, fake_llm


def _build_service_for_real_run(use_fake_rag: bool) -> ContractReviewService:
    if not settings.openai_config.api_key:
        raise ValueError("当前未配置 OPENAI_API_KEY，无法执行真实 review_contract 联调。")
    service = ContractReviewService(
        mcp_client=None,
        rag_service=_StaticFakeRagService() if use_fake_rag else None,
    )
    return service


def summarize_review_result(result: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "modification_count": len(result),
        "risk_levels": [item.get("risk_level") for item in result],
        "first_modification": result[0] if result else None,
    }


async def run_review_contract_self_test() -> dict[str, Any]:
    service, fake_llm = _build_service_for_self_test()
    result = await service.review_contract(
        model_config=SimpleNamespace(model_name="fake-contract-review-model"),
        chunk_text=DEFAULT_CHUNK_TEXT,
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


async def run_review_contract_real_validation(
    *,
    chunk_text: str,
    stance: str,
    intensity: str,
    contract_type: str,
    context: str,
    use_fake_rag: bool,
    model_name: str | None,
) -> dict[str, Any]:
    service = _build_service_for_real_run(use_fake_rag=use_fake_rag)
    resolved_model_name = model_name or settings.openai_config.model
    result = await service.review_contract(
        model_config=SimpleNamespace(model_name=resolved_model_name),
        chunk_text=chunk_text,
        stance=stance,
        intensity=intensity,
        context=context,
        contract_type=contract_type,
    )
    return {
        "model_name": resolved_model_name,
        "api_base_configured": bool(settings.openai_config.api_base),
        "api_key_configured": bool(settings.openai_config.api_key),
        "used_fake_rag": use_fake_rag,
        "result_summary": summarize_review_result(result),
        "result": result,
    }


async def _main_test_review_contract_validation():
    payload = await run_review_contract_self_test()
    result = payload["result"]
    user_prompt = payload["user_prompt"]

    assert len(result) == 2
    assert "## 外部法律依据" in user_prompt
    assert "## 内部审阅规则" in user_prompt
    assert "中华人民共和国民法典" in user_prompt
    assert "付款条款审阅规则" in user_prompt
    assert result[0]["risk_level"] == "中"
    assert result[1]["risk_level"] == "高"
    print("review_contract validation self test passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="review_contract 脱库联调与健康检查入口")
    parser.add_argument("--self-test", action="store_true", help="执行文件内自测")
    parser.add_argument("--chunk-text", default=DEFAULT_CHUNK_TEXT, help="待审阅的合同片段")
    parser.add_argument("--stance", default="甲方", help="审阅立场")
    parser.add_argument("--intensity", default="标准", help="审阅强度")
    parser.add_argument("--contract-type", default="服务类合同", help="合同类型")
    parser.add_argument("--context", default="这是第 1 个分块，共 1 个。", help="分块上下文")
    parser.add_argument("--model-name", help="覆盖默认模型名")
    parser.add_argument(
        "--no-fake-rag",
        action="store_true",
        help="关闭假 RAG，上下文中不注入外部法律和内部规则。",
    )
    args = parser.parse_args()

    if args.self_test:
        asyncio.run(_main_test_review_contract_validation())
    else:
        payload = asyncio.run(
            run_review_contract_real_validation(
                chunk_text=args.chunk_text,
                stance=args.stance,
                intensity=args.intensity,
                contract_type=args.contract_type,
                context=args.context,
                use_fake_rag=not args.no_fake_rag,
                model_name=args.model_name,
            )
        )
        print(payload)
