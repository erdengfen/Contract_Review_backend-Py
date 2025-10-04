"""
聊天服务
"""
import logging
from typing import Dict, List, Any
from datetime import datetime

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from ..core.llm import init_llm
from .contract_review import ContractReviewService
from .document_processor import DocumentProcessorService

logger = logging.getLogger(__name__)

class ChatService:
    """聊天服务"""
    
    def __init__(self, mcp_client, contract_review_service: ContractReviewService, 
                 document_processor_service: DocumentProcessorService):
        self.llm = init_llm()
        self.mcp_client = mcp_client
        self.contract_review_service = contract_review_service
        self.document_processor_service = document_processor_service
        self.sessions: Dict[str, Dict[str, Any]] = {}
    
    def get_or_create_session(self, session_id: str) -> Dict[str, Any]:
        """获取或创建会话"""
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "session_id": session_id,
                "dialogue_history": [],
                "contract_path": "",
                "contract_content": "",
                "modifications": [],
                "selected_mod_indices": [],
                "modified_contract_path": "",
                "report_path": "",
                "created_at": datetime.now().isoformat()
            }
        return self.sessions[session_id]

    
    async def process_message(self, message: str, session_id: str, action: str = "chat") -> Dict[str, Any]:
        """处理聊天消息"""
        try:
            # 获取会话
            session = self.get_or_create_session(session_id)
            
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
                    # 执行审阅
                    modifications = await self.contract_review_service.review_contract(session["contract_path"])
                    session["modifications"] = modifications
                    session["contract_content"] = await self.mcp_client.extract_document_content(session["contract_path"])
                    response_data["modifications"] = modifications
                    response_data["response"] = f"✅ 合同审阅完成！我发现了 {len(modifications)} 个需要关注的修改点。"
            
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
            
            return response_data
            
        except Exception as e:
            logger.error(f"❌ 处理聊天消息失败: {e}")
            return {
                "response": f"抱歉，处理您的请求时出现错误：{str(e)}",
                "session_id": session_id,
                "action": "error",
                "modifications": None,
                "modified_document_url": None,
                "report_url": None
            }
    
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
