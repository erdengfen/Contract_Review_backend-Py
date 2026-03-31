"""
合同审阅服务
"""
import logging
import re
import asyncio
from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from langchain_core.messages import SystemMessage, HumanMessage

try:
    from ..core.llm import init_llm
    from prompts.llm_prompt_vars import (
        REVIEW_SYSTEM_PROMPT,
        build_contract_review_prompt,
    )
except ImportError:
    from app.core.llm import init_llm
    from prompts.llm_prompt_vars import (
        REVIEW_SYSTEM_PROMPT,
        build_contract_review_prompt,
    )

logger = logging.getLogger(__name__)


class ContractReviewService:
    """合同审阅服务"""

    # 初始化函数
    def __init__(self, mcp_client):
        self.llm = init_llm()
        self.mcp_client = mcp_client

    async def review_contract(
            self,
            model_config,
            chunk_text: str,
            stance: str = "甲方",
            intensity: str = "标准",
            context: str = "",
            contract_type: str = "通用"
    ) -> List[Dict[str, Any]]:
        try:
            base_prompt_dir = Path(__file__).parent.parent.parent / "prompts"
            prompt_file_path = base_prompt_dir / "contract_reviewer_prompt_unified.txt"
            #这里的合同类型字段不知道数据库里具体叫什么名字，就按类型写在这里了
            if contract_type == "基建类合同":
                contract_type_prompt_file = "contract_reviewer_prompt_build.txt"
            elif contract_type == "货物类合同":
                contract_type_prompt_file = "contract_reviewer_prompt_sales.txt"
            elif contract_type == "服务类合同":
                contract_type_prompt_file = "contract_reviewer_prompt_service.txt"
            else:
                contract_type_prompt_file = "contract_reviewer_prompt_base.txt"

            contract_type_prompt_file_path = base_prompt_dir / contract_type_prompt_file

            with open(prompt_file_path, 'r', encoding='utf-8') as f:
                base_prompt = f.read()

            with open(contract_type_prompt_file_path, 'r', encoding='utf-8') as f:
                contract_type_prompt = f.read()

            review_prompt = build_contract_review_prompt(
                base_prompt=base_prompt,
                contract_type_prompt=contract_type_prompt,
                stance=stance,
                intensity=intensity,
                contract_type=contract_type,
                context=context,
                chunk_text=chunk_text,
            )

            messages = [
                {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
                {"role": "user", "content": review_prompt}
            ]

            response = self.llm.chat.completions.create(
                model=model_config.model_name,
                messages=messages,
                tools=[],
            )
            review_result = response.choices[0].message.content
            modifications = self._parse_review_result(review_result)

            return modifications
            
        except Exception as e:
            logger.error(f" 合同审阅失败: {e}")
            return []
    
    def _parse_review_result(self, review_result: str) -> List[Dict[str, Any]]:
        """解析审阅结果，提取修改点信息"""
        modifications = []
        
        try:
            logger.info(f" 开始解析审阅结果，原始内容长度: {len(review_result)}")
            
            # 多种格式的匹配模式
            patterns = [
                # 模式1: 【修改点X】格式
                r'【修改点(\d+)】[^\n]*\n(.*?)(?=【修改点\d+】|$)',
                # 模式2: ## 修改点X 格式
                r'##\s*修改点(\d+)[^\n]*\n(.*?)(?=##\s*修改点\d+|$)',
                # 模式3: ### 修改点X 格式
                r'###\s*修改点(\d+)[^\n]*\n(.*?)(?=###\s*修改点\d+|$)',
                # 模式4: 数字编号格式
                r'(\d+)\.\s*修改点[^\n]*\n(.*?)(?=\d+\.\s*修改点|$)',
                # 模式5: 通用标题格式
                r'[#]*\s*修改点(\d+)[^\n]*\n(.*?)(?=[#]*\s*修改点\d+|$)'
            ]
            
            matches = []
            for pattern in patterns:
                matches = re.findall(pattern, review_result, re.DOTALL)
                if matches:
                    logger.info(f" 使用模式匹配到 {len(matches)} 个修改点")
                    break
            
            if not matches:
                # 如果没有匹配到任何模式，尝试更宽松的匹配
                logger.warning("⚠ 未匹配到标准格式，尝试宽松匹配")
                
                # 尝试匹配包含"原文"、"风险"、"修改"等关键词的段落
                sections = re.split(r'\n\s*\n', review_result)
                current_mod = None
                
                for section in sections:
                    section = section.strip()
                    if not section:
                        continue
                        
                    # 检查是否是新的修改点
                    if re.search(r'修改点\s*(\d+)', section, re.IGNORECASE):
                        if current_mod:
                            modifications.append(current_mod)
                        
                        match = re.search(r'修改点\s*(\d+)', section, re.IGNORECASE)
                        current_mod = {
                            "position": f"修改点{match.group(1)}",
                            "original_content": "",
                            "risk_analysis": "",
                            "suggested_content": ""
                        }
                    
                    # 提取内容
                    if current_mod:
                        if re.search(r'原文', section, re.IGNORECASE):
                            current_mod["original_content"] = section
                        elif re.search(r'风险', section, re.IGNORECASE):
                            current_mod["risk_analysis"] = section
                        elif re.search(r'修改', section, re.IGNORECASE):
                            current_mod["suggested_content"] = section
                
                if current_mod:
                    modifications.append(current_mod)

            # 处理匹配到的修改点
            for match in matches:
                point_num = match[0]
                content = match[1].strip()
                # 提取原文、风险分析、修改后内容
                original_match = re.search(r'【?\s*原文\s*】?[：:\s]*([\s\S]*?)(?=【?\s*风险分析\s*】?|【?\s*风险等级\s*】?|【?\s*修改后的内容\s*】?|$)', content, re.DOTALL)
                if not original_match:
                    original_match = re.search(r'原文[：:]\s*(.*?)(?=风险|修改)', content, re.DOTALL)
                
                risk_match = re.search(r'【?\s*风险分析\s*】?[：:\s]*([\s\S]*?)(?=【?\s*风险等级\s*】?|【?\s*修改后的内容\s*】?|$)', content, re.DOTALL)
                if not risk_match:
                    risk_match = re.search(r'风险[：:]\s*(.*?)(?=修改)', content, re.DOTALL)
                
                modified_match = re.search(r'【?\s*修改后的内容\s*】?[：:\s]*([\s\S]*?)(?=【?\s*修改理由\s*】?|$)', content, re.DOTALL)
                if not modified_match:
                    modified_match = re.search(r'修改[：:]\s*(.*?)(?=\n|$)', content, re.DOTALL)

                # 风险等级

                level_match = re.search(r'【风险等级】[：:\s]*([\s\S]*?)(?=【修改后的内容】|【修改理由】|$)', content, re.DOTALL)
                if not level_match:
                    level_match = re.search(r'风险等级[：:\s]*([\s\S]*?)(?=【修改后的内容】|修改|【修改理由】|$)', content, re.DOTALL)

                # 修改理由
                reason_match = re.search(r'【修改理由】[：:\s]*([\s\S]*?)(?=\n*【|$)', content, re.DOTALL)
                if not reason_match:
                    reason_match = re.search(r'修改理由[：:\s]*([\s\S]*?)(?=\n*【|$)', content, re.DOTALL)

                # 风险类型
                type_match = re.search(r'【风险类型】[：:\s]*([\s\S]*?)(?=\n*【|$)', content, re.DOTALL)
                if not type_match:
                    type_match = re.search(r'风险类型[：:\s]*([\s\S]*?)(?=\n*【|$)', content, re.DOTALL)

                modification = {
                    "position": f"修改点{point_num}",
                    "original_content": original_match.group(1).strip() if original_match else "未找到原文内容",
                    "risk_analysis": risk_match.group(1).strip() if risk_match else "未找到风险分析",
                    "risk_level": level_match.group(1).strip() if level_match else "未知",
                    "suggested_content": modified_match.group(1).strip() if modified_match else "未找到修改建议",
                    "reason": reason_match.group(1).strip() if reason_match else "未找到修改理由",
                    "risk_type": type_match.group(1).strip() if type_match else "未找到风险类型"
                }

                modifications.append(modification)

            # 如果没有匹配到任何修改点，记录日志但不创建默认修改点
            if not modifications:
                logger.warning(" 未找到任何修改点，返回空列表")

            logger.info(f" 解析完成，共找到 {len(modifications)} 个修改点")

        except Exception as e:
            logger.error(f" 解析审阅结果失败: {e}")
            modifications = [
                {
                    "position": "解析错误",
                    "original_content": "解析失败",
                    "risk_analysis": "解析失败",
                    "risk_level":"未知",
                    "suggested_content": "解析失败",
                    "reason":"解析失败",
                    "risk_type":"解析失败",
                    "priority": "未知",
                    "action": "需要重新审阅"
                }
            ]

        return modifications


class _FakeChatCompletions:
    def create(self, *, model: str, messages: list, tools: list):
        fake_review_result = """
【修改点1】付款条款表述不清
【原文】乙方完成工作后甲方付款。
【风险分析】付款触发条件和付款时间不明确，容易引发履约争议。
【风险等级】中
【修改后的内容】乙方完成工作并经甲方书面验收通过后，甲方应于10个工作日内支付合同款项。
【修改理由】补足验收条件和付款期限，减少争议。
【风险类型】付款条款

【修改点2】违约责任偏弱
【原文】任何一方违约应承担责任。
【风险分析】违约责任未量化，实际追责时缺乏执行标准。
【风险等级】高
【修改后的内容】任何一方违约的，应承担守约方因此遭受的全部损失，并按合同总金额的10%支付违约金。
【修改理由】明确违约后果，提高约束力。
【风险类型】违约责任
""".strip()
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=fake_review_result)
                )
            ]
        )


class _FakeLLM:
    def __init__(self):
        self.chat = SimpleNamespace(completions=_FakeChatCompletions())


async def _main_test_review_contract():
    service = ContractReviewService.__new__(ContractReviewService)
    service.llm = _FakeLLM()
    service.mcp_client = None

    model_config = SimpleNamespace(model_name="fake-contract-review-model")
    chunk_text = """
甲方应在项目完成后向乙方付款。
任何一方违约应承担责任。
""".strip()

    result = await service.review_contract(
        model_config=model_config,
        chunk_text=chunk_text,
        stance="甲方",
        intensity="标准",
        context="这是第 1 个分块，共 1 个。",
        contract_type="服务类合同",
    )

    print("review_contract test result:")
    for item in result:
        print(item)

    assert len(result) == 2, f"expected 2 modifications, got {len(result)}"
    assert result[0]["risk_level"] == "中"
    assert result[1]["risk_level"] == "高"
    print("review_contract smoke test passed")


if __name__ == "__main__":
    asyncio.run(_main_test_review_contract())
