"""
聊天服务
"""
import logging
import os
from typing import Dict, List, Any
from datetime import datetime

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from ..core.llm import init_llm
from .contract_review import ContractReviewService
from .document_processor import DocumentProcessorService
from .enhanced_memory_service import EnhancedMemoryService
from ..utils.content_slicer import split_text_by_length

logger = logging.getLogger(__name__)

class ChatService:
    """聊天服务"""
    
    def __init__(self, mcp_client, contract_review_service: ContractReviewService, 
                 document_processor_service: DocumentProcessorService, memory_service: EnhancedMemoryService):
        self.llm = init_llm()
        self.mcp_client = mcp_client
        self.contract_review_service = contract_review_service
        self.document_processor_service = document_processor_service
        self.memory_service = memory_service
    
    def get_or_create_session(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """获取或创建会话"""
        return self.memory_service.get_or_create_user_session(user_id, session_id)

    
    async def process_message(self, message: str, user_id: str, session_id: str, action: str = "chat", role: str = "甲方", contract_type: str = "") -> Dict[str, Any]:
        """处理聊天消息"""
        try:
            # 获取会话
            session = self.get_or_create_session(user_id, session_id)
            
            # 添加用户消息到对话历史
            session["dialogue_history"].append({"role": "user", "content": message})
            
            # 构建对话上下文
            context = {

                "dialogue_history": session["dialogue_history"],
                "contract_content": session.get("contract_content", ""),
                "modifications": session.get("modifications", []),
                "contract_path": session.get("contract_path", ""),
                "has_file": bool(session.get("contract_path"))
            }
            
            # 获取大模型响应
            llm_response = await self._get_llm_response(message, context)
            
            # 解析用户意图
            intent_result = await self._parse_user_intent(message, llm_response)
            intent = intent_result.get("intent", "chat")
            action_type = intent_result.get("action", "continue_dialogue")
            
            # 根据意图执行相应操作
            response_data = {
                "response": llm_response,
                "session_id": session_id,
                "action": action_type,
                "modifications": None,
                "modified_document_url": None,
                "report_url": None
            }
            
            if intent == "review" and action_type == "start_review":
                    # 开始审阅流程
                    if not session.get("contract_path"):
                        response_data["response"] = "请先上传合同文件，然后我可以帮您审阅。"
                    else:
                        contract_path = session["contract_path"]
                        file_ext = os.path.splitext(contract_path)[1].lower()
                        if file_ext == ".pdf":
                            #提取pdf文档内容
                            contract_content = await self.mcp_client.extract_pdf_document_content(session["contract_path"])
                        else:
                            # 提取合同内容
                            contract_content = await self.mcp_client.extract_document_content(session["contract_path"])
                        
                        # 保存合同内容到会话
                        self.memory_service.update_user_session(user_id, session_id, {
                            "contract_content": contract_content
                        })
                        
                        # 保存合同分块到数据库
                        saved_chunks = self.memory_service.save_contract_chunks(user_id, session_id, contract_content)
                        logger.info(f"📄 合同分割为 {len(saved_chunks)} 个分块")
                        
                        # 审阅每个分块
                        all_modifications = []
                        for idx, chunk_data in enumerate(saved_chunks):
                            # 构建审阅上下文
                            context = self.memory_service.build_review_context(user_id, session_id, idx)
                            
                            # 执行审阅
                            modifications = await self.contract_review_service.review_contract(
                                chunk_data["chunk_content"], role, contract_type, context
                            )
                            
                            # 保存审阅结果
                            review_result = str(modifications)  # 将修改建议转换为字符串存储
                            self.memory_service.save_review_result(user_id, session_id, idx, review_result)
                            
                            all_modifications.extend(modifications)
                            
                            yield {
                                "response": f"第 {idx + 1}/{len(saved_chunks)} 段审阅完成，发现 {len(modifications)} 个修改点。",
                                "user_id": user_id,
                                "session_id": session_id,
                                "action": "reviewing",
                                "modifications": modifications,
                                "modified_document_url": None,
                                "report_url": None
                            }
                        
                        # 更新会话中的修改建议
                        self.memory_service.update_user_session(user_id, session_id, {
                            "modifications": all_modifications
                        })
                        
                        yield {
                            "response": f"全部审阅完成，共发现 {len(all_modifications)} 个修改点。",
                            "user_id": user_id,
                            "session_id": session_id,
                            "action": "review_complete"
                        }
            
            elif intent == "modify" and action_type == "apply_modifications":
                # 修改合同
                if not session.get("modifications"):
                    response_data["response"] = "请先让我审阅合同，然后我可以为您提供修改建议。"
                else:
                    # 执行修改
                    result = await self.document_processor_service.modify_document(
                        session["contract_path"],
                        session["modifications"],
                        session.get("selected_mod_indices", []),
                        "output/results"
                    )
                    session["modified_contract_path"] = result.get("modified_contract_path", "")
                    session["report_path"] = result.get("report_path", "")
                    response_data["modified_document_url"] = f"/api/download/{session_id}/modified"
                    response_data["report_url"] = f"/api/download/{session_id}/report"
                    response_data["response"] = "✅ 文档修改完成！修改后的合同和报告已生成。"
            
            # 添加助手响应到对话历史
            session["dialogue_history"].append({"role": "assistant", "content": response_data["response"]})
            
            return
            
        except Exception as e:
            logger.error(f"❌ 处理聊天消息失败: {e}")
            yield {
                "response": f"抱歉，处理您的请求时出现错误：{str(e)}",
                "session_id": session_id,
                "action": "error",
                "modifications": None,
                "modified_document_url": None,
                "report_url": None
            }
            return
    
    async def _get_llm_response(self, user_input: str, context: Dict[str, Any]) -> str:
        """获取大模型的对话响应"""
        try:
            # 构建对话上下文
            dialogue_history = context.get("dialogue_history", [])
            contract_content = context.get("contract_content", "")
            modifications = context.get("modifications", [])
            
            # 构建系统提示词
            system_prompt = """你是一个专业的合同审阅助手，具有以下能力：
1. 与用户进行自然对话，理解用户的需求和意图
2. 审阅合同文档，识别潜在的法律风险和问题
3. 提供专业的修改建议和解释
4. 根据用户的确认执行具体的修改操作
5. 在修改位置添加标记，让用户清楚看到修改内容

请以友好、专业的方式与用户对话，根据用户的需求提供相应的帮助。"""
            
            # 构建对话历史
            messages = [SystemMessage(content=system_prompt)]
            
            # 添加对话历史
            for msg in dialogue_history[-10:]:  # 只保留最近10轮对话
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))
            
            # 添加当前用户输入
            messages.append(HumanMessage(content=user_input))
            
            # 如果有合同内容，添加到上下文中
            if contract_content:
                messages.append(SystemMessage(content=f"当前合同内容摘要：\n{contract_content[:1000]}..."))
            
            # 如果有修改建议，添加到上下文中
            if modifications:
                mod_summary = "当前修改建议：\n"
                for i, mod in enumerate(modifications[:5], 1):
                    mod_summary += f"{i}. {mod.get('position', f'修改点{i}')}\n"
                messages.append(SystemMessage(content=mod_summary))
            
            # 调用大模型
            response = self.llm.invoke(messages)
            return response.content.strip()
            
        except Exception as e:
            logger.error(f"❌ 获取大模型响应失败: {e}")
            return "抱歉，我遇到了一些技术问题，请稍后再试。"
    
    async def _parse_user_intent(self, user_input: str, llm_response: str) -> Dict[str, Any]:
        """解析用户意图，判断是否需要执行特定操作"""
        try:
            # 简单的关键词匹配来判断意图
            user_input_lower = user_input.lower()
            
            # 检查是否是退出意图
            if any(word in user_input_lower for word in ["结束", "退出", "再见", "结束对话", "exit", "quit"]):
                return {"intent": "end", "action": "exit"}
            
            # 检查是否是审阅意图
            if any(word in user_input_lower for word in ["审阅", "分析", "检查", "看看", "帮我看看", "分析一下"]):
                return {"intent": "review", "action": "start_review"}
            
            # 检查是否是修改意图
            if any(word in user_input_lower for word in ["修改", "改", "调整", "优化", "应用", "执行"]):
                return {"intent": "modify", "action": "apply_modifications"}
            
            # 检查是否是查询意图
            if any(word in user_input_lower for word in ["查看", "显示", "列出", "有什么", "哪些"]):
                return {"intent": "query", "action": "show_info"}
            
            # 检查是否是确认意图
            if any(word in user_input_lower for word in ["确认", "同意", "是的", "好的", "可以", "执行"]):
                return {"intent": "confirm", "action": "confirm_action"}
            
            # 检查是否是拒绝意图
            if any(word in user_input_lower for word in ["不", "不要", "拒绝", "取消", "算了"]):
                return {"intent": "reject", "action": "cancel_action"}
            
            # 默认是普通对话
            return {"intent": "chat", "action": "continue_dialogue"}
            
        except Exception as e:
            logger.error(f"❌ 解析用户意图失败: {e}")
            return {"intent": "chat", "action": "continue_dialogue"}
