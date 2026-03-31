from textwrap import dedent


CONTRACT_INFO_EXTRACTION_SYSTEM_PROMPT = dedent(
    """
    你是一个专业的合同信息提取引擎，请严格遵守以下规则：

    1. **仅处理合同类文档**。如果输入内容不是合同（如论文、通知、模板等），请返回：
    ```json
    {
        "party_a": "{未识别}",
        "party_b": "{未识别}",
        "amount": "{未识别}"
    }
    ```
    2. **必须以纯 JSON 格式输出，且仅包含以下三个字段**：
       - "party_a": 甲方全称（字符串）
       - "party_b": 乙方全称（字符串）
       - "amount": 合同金额及单位（字符串，如 "50000元"）

    3. **字段规则**：
       - 若无法识别某字段，值为 "{未识别}"
       - 不要包含任何额外字段、注释、markdown、换行或说明文字
       - 输出必须是合法 JSON
       - 金额字段必须包含单位（"元"）
    4. **禁止行为**：
       - 禁止输出非 JSON 内容（如“好的，结果如下：”）
       - 禁止推测、虚构信息
       - 禁止使用中文引号、单引号（必须双引号）

    5. **正确示例**：
    ```json
    {
        "party_a": "华为技术有限公司",
        "party_b": "中国移动通信集团",
        "amount": "12500000元"
    }
    ```
    """
).strip()


def build_contract_info_extraction_user_prompt(contract_content: str) -> str:
    return f"请提取以下文档中的合同信息：\n\n{contract_content[:5000]}"


CONTRACT_PARTY_EXTRACTION_SYSTEM_PROMPT = "你是一个专业的合同信息提取助手。"

CONTRACT_PARTY_EXTRACTION_BASE_PROMPT = dedent(
    """
    你是一名专业的合同律师。请从以下合同内容中提取出甲方和乙方的名称以及合同金额（如果有简称，也一并标注）。
    请严格以 JSON 格式输出结果，不要包含其他文字、说明或 Markdown 代码块。输出示例如下：
    {
      "party_a": "xxx公司",
      "party_b": "yyy公司",
      "contract_value": "XXX"
    }
    如果未找到，则用空字符串代替。
    """
).strip()


def build_contract_party_extraction_user_prompt(sample_text: str) -> str:
    return f"{CONTRACT_PARTY_EXTRACTION_BASE_PROMPT}\n\n合同内容:\n{sample_text}"


REVIEW_SYSTEM_PROMPT = "你是一个专业的合同审查律师，请严格按照提示词要求进行合同审阅。"

REVIEW_INTENSITY_DESC_MAP = {
    "严格": "请进行严格审阅，覆盖全部审查维度，识别所有潜在法律与履约风险，包括措辞模糊、权利不对等等细节问题。",
    "标准": "请进行标准审阅，重点关注7个核心风险领域（交付、质量、违约、知识产权、保密、争议解决、生效要件）。",
    "宽松": "请进行宽松审阅，仅指出重大法律风险（如无效免责、管辖不明、主体缺失、违约无责等），忽略一般性模糊表述。",
}


def build_review_context_info(context: str) -> str:
    if not context:
        return ""
    return dedent(
        f"""
        ## 审阅上下文
        {context}

        请结合上述上下文信息，确保审阅的连续性和一致性。
        """
    ).strip()


def build_contract_review_prompt(
    *,
    base_prompt: str,
    contract_type_prompt: str,
    stance: str,
    intensity: str,
    contract_type: str,
    context: str,
    chunk_text: str,
) -> str:
    intensity_desc = REVIEW_INTENSITY_DESC_MAP.get(
        intensity,
        REVIEW_INTENSITY_DESC_MAP["标准"],
    )
    context_info = build_review_context_info(context)
    prompt_body = dedent(
        f"""
        ## 任务要求
        - 用户立场：{stance}
        - 审查强度：{intensity}
        - 合同类型：{contract_type}
        - 审阅要点：{contract_type_prompt}
        - {intensity_desc}

        {context_info}

        ## 合同内容
        {chunk_text}
        请严格按照上述格式要求输出审阅结果。每个修改点必须包含：
        1. 【修改点X】
        2. 【原文】（100字以内）
        3. 【风险分析】
        4. 【风险等级】
        5. 【修改后的内容】
        6. 【修改理由】
        7. 【风险类型】（15字内）
        确保分析专业、建议可行、格式规范。
        """
    ).strip()
    return f"{base_prompt.format(stance=stance)}\n\n{prompt_body}"
