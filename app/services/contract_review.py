"""
合同审阅服务
"""
import logging
import re
from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path

from langchain_core.messages import SystemMessage, HumanMessage
from ..core.llm import init_llm
from ..utils.mcp_client import MCPClient

logger = logging.getLogger(__name__)

class ContractReviewService:
    """合同审阅服务"""
    
    def __init__(self, mcp_client: MCPClient):
        self.llm = init_llm()
        self.mcp_client = mcp_client
    
    async def review_contract(self, contract_path: str) -> List[Dict[str, Any]]:
        """执行合同审阅"""
        try:
            # 提取合同内容
            contract_content = await self.mcp_client.extract_document_content(contract_path)
            
            # 构建审阅提示词
            prompt_file_path = Path(__file__).parent.parent.parent / "prompts" / "contract_reviewer_prompt.txt"
            try:
                with open(prompt_file_path, 'r', encoding='utf-8') as f:
                    base_prompt = f.read()
            except FileNotFoundError:
                base_prompt = "你是一个专业的合同审查律师，请对以下合同进行专业审阅。"
            
            review_prompt = f"""{base_prompt}

## 任务要求
请对以下合同进行专业审阅：

## 合同内容
```
{contract_content}
```

请严格按照上述格式要求输出审阅结果。每个修改点必须包含：
1. 【修改点X】- 修改点编号和标题
2. 【原文】- 原始条款内容
3. 【风险分析】- 法律风险分析
4. 【修改后的内容】- 建议的修改内容

请确保分析专业、建议可行、格式规范。
"""

            messages = [
                SystemMessage(content="你是一个专业的合同审查律师，请严格按照提示词要求进行合同审阅。"),
                HumanMessage(content=review_prompt)
            ]

            # 调用模型并解析结果
            response = self.llm.invoke(messages)
            review_result = response.content
            modifications = self._parse_review_result(review_result)
            
            return modifications
            
        except Exception as e:
            logger.error(f"❌ 合同审阅失败: {e}")
            return []
    
    def _parse_review_result(self, review_result: str) -> List[Dict[str, Any]]:
        """解析审阅结果，提取修改点信息"""
        modifications = []
        
        try:
            logger.info(f"🔍 开始解析审阅结果，原始内容长度: {len(review_result)}")
            
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
                    logger.info(f"✅ 使用模式匹配到 {len(matches)} 个修改点")
                    break
            
            if not matches:
                # 如果没有匹配到任何模式，尝试更宽松的匹配
                logger.warning("⚠️ 未匹配到标准格式，尝试宽松匹配")
                
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
                            "suggested_content": "",
                            "priority": "中",
                            "action": "建议修改"
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
                original_match = re.search(r'【原文】\n(.*?)(?=【风险分析】|【修改后的内容】)', content, re.DOTALL)
                if not original_match:
                    original_match = re.search(r'原文[：:]\s*(.*?)(?=风险|修改)', content, re.DOTALL)
                
                risk_match = re.search(r'【风险分析】\n(.*?)(?=【修改后的内容】)', content, re.DOTALL)
                if not risk_match:
                    risk_match = re.search(r'风险[：:]\s*(.*?)(?=修改)', content, re.DOTALL)
                
                modified_match = re.search(r'【修改后的内容】\n(.*?)(?=\n|$)', content, re.DOTALL)
                if not modified_match:
                    modified_match = re.search(r'修改[：:]\s*(.*?)(?=\n|$)', content, re.DOTALL)
                
                modification = {
                    "position": f"修改点{point_num}",
                    "original_content": original_match.group(1).strip() if original_match else "未找到原文内容",
                    "risk_analysis": risk_match.group(1).strip() if risk_match else "未找到风险分析",
                    "suggested_content": f"***{modified_match.group(1).strip()}***" if modified_match else "未找到修改建议",
                    "priority": "中",
                    "action": "建议修改"
                }
                
                modifications.append(modification)
            
            # 如果没有匹配到任何修改点，记录日志但不创建默认修改点
            if not modifications:
                logger.warning("⚠️ 未找到任何修改点，返回空列表")
            
            logger.info(f"✅ 解析完成，共找到 {len(modifications)} 个修改点")
            
        except Exception as e:
            logger.error(f"❌ 解析审阅结果失败: {e}")
            modifications = [
                {
                    "position": "解析错误",
                    "original_content": "解析失败",
                    "risk_analysis": "解析失败",
                    "suggested_content": "解析失败",
                    "priority": "未知",
                    "action": "需要重新审阅"
                }
            ]
        
        return modifications
