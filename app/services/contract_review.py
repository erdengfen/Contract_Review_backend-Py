"""
合同审阅服务
"""
import logging
import re
from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path

from fastapi.params import Depends
from langchain_core.messages import SystemMessage, HumanMessage

from ..core.dependencies import get_db
from ..core.global_init import llm_manager
from ..models import Session
from ..utils.mcp_client import MCPClient
#from ..utils.content_slicer import split_text_by_length

logger = logging.getLogger(__name__)

class ContractReviewService:
    """合同审阅服务"""
    #初始化函数
    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client

    async def review_contract(self, user_id: int ,chunk_text: str, stance: str = "甲方", intensity: str = "标准",
                            context: str = "", db:Session = Depends(get_db)) -> List[Dict[str, Any]]:
        """执行合同审阅"""
        try:
            # 构建审阅提示词
            base_prompt_dir = Path(__file__).parent.parent.parent / "prompts"
            # 根据审阅尺度选择不同的提示词
            if intensity == "严格":
                prompt_file_path = base_prompt_dir / "contract_reviewer_prompt_service.txt"
            elif intensity == "宽松":
                prompt_file_path = base_prompt_dir / "contract_reviewer_prompt_sales.txt"
            else:
                prompt_file_path = base_prompt_dir / "contract_reviewer_prompt_base.txt"

            try:
                with open(prompt_file_path, 'r', encoding='utf-8') as f:
                    base_prompt = f.read()
            except FileNotFoundError:
                base_prompt = "你是一个专业的合同审查律师，请对以下合同进行专业审阅。"

            # 构建上下文信息
            context_info = ""
            if context:
                context_info = f"""

## 审阅上下文
{context}

请结合上述上下文信息，确保审阅的连续性和一致性。
"""

            # 根据审阅尺度调整提示词强度
            intensity_desc = {
                "严格": "请进行严格审阅，重点关注所有潜在风险点，包括细微的法律风险",
                "标准": "请进行标准审阅，重点关注主要风险点",
                "宽松": "请进行宽松审阅，重点关注重大风险点"
            }
            
            review_prompt = f"""{base_prompt}

## 任务要求
用户是{stance}，请从{stance}的角度分析合同风险。审阅尺度：{intensity}。
{intensity_desc.get(intensity, "请进行标准审阅")}

对以下合同进行专业审阅：{context_info}

## 合同内容
```
{chunk_text}
```

请严格按照上述格式要求输出审阅结果。每个修改点必须包含：
1. 【修改点X】- 修改点编号和标题
2. 【原文】- 原始条款内容
3. 【风险分析】- 法律风险分析
4. 【风险等级】- （高/中/低；含评分 0–100）
5. 【修改后的内容】- 建议的修改内容
6. 【修改理由】- 说明法律条文与商业合理性

请确保分析专业、建议可行、格式规范。结合上下文信息，保持审阅的连贯性。
"""

            messages = [
                SystemMessage(content="你是一个专业的合同审查律师，请严格按照提示词要求进行合同审阅。"),
                HumanMessage(content=review_prompt)
            ]

            # 调用模型并解析结果
            llm = await llm_manager.get_user_llm(user_id=user_id, db_session=db)
            response = llm.invoke(messages)
            review_result = response.content
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

                modification = {
                    "position": f"修改点{point_num}",
                    "original_content": original_match.group(1).strip() if original_match else "未找到原文内容",
                    "risk_analysis": risk_match.group(1).strip() if risk_match else "未找到风险分析",
                    "risk_level": level_match.group(1).strip() if level_match else "未知",
                    "suggested_content": modified_match.group(1).strip() if modified_match else "未找到修改建议",
                    "reason": reason_match.group(1).strip() if reason_match else "未找到修改理由"
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
                    "priority": "未知",
                    "action": "需要重新审阅"
                }
            ]

        return modifications
