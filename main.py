#!/usr/bin/env python3
"""
法务合同审阅系统 - API接口版本
支持前端调用，提供合同审阅和修改服务
"""

import os
import asyncio
import logging
from typing import Dict, List, Any, Optional, TypedDict, Annotated
from pathlib import Path
import json
from datetime import datetime
import re
import uuid

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from langgraph.checkpoint.memory import InMemorySaver
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv

# LangGraph相关导入
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent

load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 获取环境变量
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
MCP_SERVER_URL = os.getenv('MCP_SERVER_URL', 'http://127.0.0.1:8081/mcp/')

# 创建FastAPI应用
app = FastAPI(title="合同审阅系统API", version="1.0.0")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API请求/响应模型
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    action: Optional[str] = "chat"  # chat, review, modify, export

class ChatResponse(BaseModel):
    response: str
    session_id: str
    action: str
    modifications: Optional[List[Dict[str, Any]]] = None
    modified_document_url: Optional[str] = None
    report_url: Optional[str] = None

class UploadResponse(BaseModel):
    success: bool
    message: str
    session_id: str
    document_id: str

# 尝试导入create_react_agent，如果失败则使用备选方案
try:
    from langgraph.prebuilt import create_react_agent
    REACT_AGENT_AVAILABLE = True
    logger.info("✅ create_react_agent 可用")
except ImportError:
    REACT_AGENT_AVAILABLE = False
    logger.warning("⚠️ create_react_agent 不可用，将使用备选方案")

# 初始化LLM的函数
def init_llm():
    """初始化LLM"""
    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY环境变量未设置")
    
    return init_chat_model(
        model="deepseek-chat",
        temperature=0,
        model_provider="deepseek",
    )

# 定义状态类型
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    contract_path: str
    output_dir: str
    review_data: Dict[str, Any]
    current_step: str
    modifications: List[Dict[str, Any]]
    modified_contract_path: str
    report_path: str
    contract_content: str             # 合同内容
    #
    user_input_required: bool          # 是否强制对话（始终 True）
    dialogue_history: List[Dict[str, str]]  # [{'role': 'user'|'assistant', 'content': str}]
    selected_mod_indices: List[int]
    intent: str                        # 用户意图：review, modify, query, export, end
    slots: Dict[str, Any]             # 槽位信息：target_clause, scope, selection_add, selection_remove, apply_changes, format, export
    confirmed_scope: str               # 已确认的修改范围
    session_id: str                   # 会话ID
    has_file: bool                    # 是否已上传文件

class MultiAgentContractReviewSystem:
    """多智能体合同审阅系统 - API版本"""
    
    def __init__(self):
        self.llm = init_llm()
        self.mcp_client = None
        self.tools = []
        self.graph = None
        self.checkpointer = InMemorySaver()
        self.session_dir = Path("output/sessions")
        self.session_dir.mkdir(exist_ok=True)
        self.upload_dir = Path("output/uploads")
        self.upload_dir.mkdir(exist_ok=True)
        self.output_dir = Path("output/results")
        self.output_dir.mkdir(exist_ok=True)
        
        # 会话存储
        self.sessions: Dict[str, Dict[str, Any]] = {}
    
    async def initialize_system(self):
        """初始化系统"""
        try:
            # 初始化MCP客户端
            await self.initialize_mcp_client()
            # 创建多智能体图
            self.create_multi_agent_graph()
            logger.info("✅ 系统初始化完成")
            return True
        except Exception as e:
            logger.error(f"❌ 系统初始化失败: {e}")
            return False
    
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
    
    async def process_chat_message(self, message: str, session_id: str, action: str = "chat") -> Dict[str, Any]:
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
                    modifications = await self._perform_contract_review(session)
                    session["modifications"] = modifications
                    response_data["modifications"] = modifications
                    response_data["response"] = f"✅ 合同审阅完成！我发现了 {len(modifications)} 个需要关注的修改点。"
            
            elif intent == "modify" and action_type == "apply_modifications":
                # 修改合同
                if not session.get("modifications"):
                    response_data["response"] = "请先让我审阅合同，然后我可以为您提供修改建议。"
                else:
                    # 执行修改
                    result = await self._perform_document_modification(session)
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
    
    async def _perform_contract_review(self, session: Dict[str, Any]) -> List[Dict[str, Any]]:
        """执行合同审阅"""
        try:
            contract_path = session["contract_path"]
            
            # 提取合同内容
            contract_content = await self._extract_document_content(contract_path)
            session["contract_content"] = contract_content
            
            # 构建审阅提示词
            prompt_file_path = Path(__file__).parent / "prompts" / "contract_reviewer_prompt.txt"
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
    
    async def _perform_document_modification(self, session: Dict[str, Any]) -> Dict[str, str]:
        """执行文档修改"""
        try:
            contract_path = session["contract_path"]
            modifications = session["modifications"]
            selected_indices = session.get("selected_mod_indices", [])
            
            # 创建修改后的文档
            modified_filename = f"modified_{Path(contract_path).name}"
            modified_path = self.output_dir / modified_filename
            
            # 复制文档
            await self._call_mcp_tool("copy_document", {
                "source_filename": contract_path,
                "destination_filename": str(modified_path)
            })
            
            # 应用修改
            for idx in selected_indices:
                if 0 <= idx < len(modifications):
                    mod = modifications[idx]
                    original = mod.get("original_content", "").strip()
                    suggested = mod.get("suggested_content", "").strip()
                    
                    if original and suggested:
                        # 搜索替换
                        await self._call_mcp_tool("search_and_replace", {
                            "filename": str(modified_path),
                            "find_text": original,
                            "replace_text": suggested
                        })
                        
                        # 格式化修改后的文本
                        try:
                            matches = await self._call_mcp_tool("find_text_in_document", {
                                "filename": str(modified_path),
                                "text_to_find": suggested,
                                "match_case": False,
                                "whole_word": False
                            })
                            
                            if isinstance(matches, dict):
                                match_list = matches.get("matches", [])
                            else:
                                match_list = matches or []
                                
                            for m in match_list[:3]:
                                await self._call_mcp_tool("format_text", {
                                    "filename": str(modified_path),
                                    "paragraph_index": int(m.get("paragraph_index", 0)),
                                    "start_pos": int(m.get("start_pos", 0)),
                                    "end_pos": int(m.get("end_pos", 0)),
                                    "color": "FF0000",
                                    "bold": True
                                })
                        except Exception as fe:
                            logger.warning(f"格式化失败: {fe}")
            
            # 生成报告
            report_path = self._generate_report(session, str(modified_path))
            
            return {
                "modified_contract_path": str(modified_path),
                "report_path": report_path
            }
            
        except Exception as e:
            logger.error(f"❌ 文档修改失败: {e}")
            return {"modified_contract_path": "", "report_path": ""}
    
    def _generate_report(self, session: Dict[str, Any], modified_path: str) -> str:
        """生成审阅报告"""
        try:
            modifications = session.get("modifications", [])
            contract_name = Path(session["contract_path"]).stem
            
            report_content = f"""# 合同审阅报告

**审阅时间**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
**合同文件**: {contract_name}
**修改后文件**: {Path(modified_path).name}

共识别出 {len(modifications)} 条修改建议：

"""
            
            for i, mod in enumerate(modifications, 1):
                report_content += f"""## 【修改点{i}】- {mod.get('position', f'修改点{i}')}

### 【原文】
{mod.get('original_content', '未知')}

### 【风险分析】
{mod.get('risk_analysis', '未知')}

### 【修改后的内容】
{mod.get('suggested_content', '未知')}

---
"""
            
            report_content += f"""
## 总结

共提出 {len(modifications)} 条修改建议，建议根据上述分析对合同进行相应调整。

---
*本报告由AI法务合同审阅系统生成，仅供参考。具体法律意见请咨询专业律师。*
"""
            
            # 保存报告
            report_path = self.output_dir / f"contract_review_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            return str(report_path)
            
        except Exception as e:
            logger.error(f"❌ 生成报告失败: {e}")
            return ""
        
    def _save_session_state(self, state: AgentState):
        """保存会话状态到文件"""
        try:
            session_id = state.get("session_id", "default")
            session_file = self.session_dir / f"session_{session_id}.json"
            
            # 准备保存的数据（排除不可序列化的对象）
            save_data = {
                "session_id": state.get("session_id", ""),
                "contract_path": state.get("contract_path", ""),
                "output_dir": state.get("output_dir", ""),
                "review_data": state.get("review_data", {}),
                "current_step": state.get("current_step", ""),
                "modifications": state.get("modifications", []),
                "modified_contract_path": state.get("modified_contract_path", ""),
                "report_path": state.get("report_path", ""),
                "dialogue_history": state.get("dialogue_history", []),
                "selected_mod_indices": state.get("selected_mod_indices", []),
                "intent": state.get("intent", ""),
                "slots": state.get("slots", {}),
                "confirmed_scope": state.get("confirmed_scope", ""),
                "has_file": state.get("has_file", False),
                "timestamp": datetime.now().isoformat()
            }
            
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 会话状态已保存: {session_file}")
            
        except Exception as e:
            logger.error(f"❌ 保存会话状态失败: {e}")

    def _load_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """从文件加载会话状态"""
        try:
            session_file = self.session_dir / f"session_{session_id}.json"
            if session_file.exists():
                with open(session_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None
        except Exception as e:
            logger.error(f"❌ 加载会话状态失败: {e}")
            return None

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

    async def _call_mcp_tool(self, tool_name: str, arguments: dict) -> Any:
        """调用MCP工具的通用方法"""
        try:
            # 直接调用工具对象
            tool = next((t for t in self.tools if t.name == tool_name), None)
            if tool:
                return await tool.ainvoke(arguments)
            else:
                raise Exception(f"找不到工具: {tool_name}")
        except Exception as e:
            logger.error(f"调用MCP工具 {tool_name} 失败: {e}")
            raise



    async def _extract_document_content(self, file_path: str) -> str:
        """直接调用MCP工具提取文档内容"""
        if not self.mcp_client or not self.tools:
            raise Exception("MCP客户端未初始化")
        
        try:
            # 直接调用get_document_text工具
            logger.info(f"🔧 调用工具: get_document_text")
            result = await self._call_mcp_tool("get_document_text", {"filename": file_path})
            
            if result:
                content = str(result)
                logger.info(f"✅ 成功提取文档内容，长度: {len(content)} 字符")
                return content
            else:
                raise Exception("工具返回空结果")
                
        except Exception as e:
            logger.error(f"❌ 直接调用工具失败: {e}")
            raise Exception(f"无法提取文档内容: {e}")

    async def initialize_mcp_client(self):
        """初始化MCP客户端"""
        try:
            # 实例化MCP Server客户端
            self.mcp_client = MultiServerMCPClient({
                "office-word-mcp": {
                    "url": MCP_SERVER_URL,
                    "transport": "streamable_http",
                }
            })
            
            # 从MCP Server中获取可提供使用的全部工具
            self.tools = await self.mcp_client.get_tools()
            logger.info(f"✅ MCP客户端初始化成功，获取到 {len(self.tools)} 个工具")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ MCP客户端初始化失败: {e}")
            return False
    
    def create_multi_agent_graph(self):
        """创建多智能体图"""
        # 创建工作流图
        workflow = StateGraph(AgentState)
        
        # 添加节点
        workflow.add_node("contract_reviewer", self.contract_reviewer_agent)
        workflow.add_node("document_processor", self.document_processor_agent)
        workflow.add_node("supervisor", self.supervisor_agent)
        
        # 设置入口点
        workflow.set_entry_point("supervisor")

        # 设置条件边 - 修复循环问题
        workflow.add_conditional_edges(
            "supervisor",
            self.should_continue,
            {
                "continue": "contract_reviewer",
                "end": END
            }
        )
        
        # 添加其他边
        workflow.add_edge("contract_reviewer", "document_processor")
        workflow.add_edge("document_processor", "supervisor")
        
        # 编译图
        self.graph = workflow.compile(checkpointer=self.checkpointer)
        logger.info("✅ 多智能体图创建成功")
    
    def should_continue(self, state: AgentState) -> str:
        """决定是否继续执行"""
        current_step = state.get("current_step", "")
        
        logger.info(f"🔍 should_continue检查: current_step = {current_step}")
        
        if current_step == "completed":
            logger.info("✅ 流程已完成，返回end")
            return "end"
        elif current_step == "review_completed":
            logger.info("📋 审阅已完成，继续到文档处理")
            return "continue"
        elif current_step == "document_processing_completed":
            logger.info("✅ 文档处理已完成，返回end")
            return "end"
        else:
            logger.info("🔄 继续执行")
            return "continue"
    
    async def supervisor_agent(self, state: AgentState) -> AgentState:
        """监督者智能体 - 对话式合同审阅助手"""
        logger.info("🎯 进入监督者智能体节点")
        
        # 获取用户输入
        if not state.get("dialogue_history") or len(state["dialogue_history"]) == 0:
            print("\n🤖 您好！我是您的专业合同审阅助手")
            print("💡 我可以帮助您：")
            print("  • 审阅合同文档，识别法律风险")
            print("  • 提供专业的修改建议")
            print("  • 根据您的确认执行修改操作")
            print("  • 在修改位置添加标记，让您清楚看到变化")
            print("  • 与您进行自然对话，理解您的需求")
            print("-" * 60)
            
            user_input = input("\n👤 请告诉我您需要什么帮助: ").strip()
            if not user_input:
                print("❌ 输入不能为空，请重新输入")
                return state
                
            # 添加到对话历史
            state["dialogue_history"].append({"role": "user", "content": user_input})
        else:
            # 继续对话
            user_input = input("\n👤 请继续告诉我您的需求: ").strip()
            if not user_input:
                print("❌ 输入不能为空，请重新输入")
                return state
                
            # 添加到对话历史
            state["dialogue_history"].append({"role": "user", "content": user_input})
        
        # 构建对话上下文
        context = {
            "dialogue_history": state.get("dialogue_history", []),
            "contract_content": state.get("contract_content", ""),
            "modifications": state.get("modifications", []),
            "contract_path": state.get("contract_path", ""),
            "has_file": state.get("has_file", False)
        }
        
        # 获取大模型的对话响应
        llm_response = await self._get_llm_response(user_input, context)
        
        # 解析用户意图
        intent_result = await self._parse_user_intent(user_input, llm_response)
        intent = intent_result.get("intent", "chat")
        action = intent_result.get("action", "continue_dialogue")
        
        print(f"\n🤖 助手: {llm_response}")
        
        # 根据意图执行相应操作
        if intent == "end":
            print("\n👋 感谢使用智能合同审阅系统，再见！")
            state["current_step"] = "completed"
            return state
            
        elif intent == "review" and action == "start_review":
            # 开始审阅流程
            if not state.get("has_file"):
                print("❌ 请先选择合同文件")
                state["dialogue_history"].append({"role": "assistant", "content": "请先选择合同文件，然后我可以帮您审阅。"})
                return state
                
            state["current_step"] = "review_started"
            state["review_data"] = {
                "contract_info": {},
                "modifications": [],
                "conversation_history": state["dialogue_history"]
            }
            
            print("📋 开始合同审阅流程...")
            return state
            
        elif intent == "modify" and action == "apply_modifications":
            # 修改合同
            if not state.get("modifications"):
                print("❌ 请先进行合同审阅")
                state["dialogue_history"].append({"role": "assistant", "content": "请先让我审阅合同，然后我可以为您提供修改建议。"})
                return state
                
            print("✏️ 开始文档修改流程...")
            state["current_step"] = "document_processing_started"
            return state
            
        elif intent == "query" and action == "show_info":
            # 查询信息
            if state.get("modifications"):
                print(f"\n📊 当前发现 {len(state['modifications'])} 个修改点:")
                for i, mod in enumerate(state["modifications"][:5], 1):
                    print(f"  {i}. {mod.get('position', f'修改点{i}')}")
                if len(state["modifications"]) > 5:
                    print(f"  ... 还有 {len(state['modifications']) - 5} 个修改点")
            else:
                print("📋 尚未进行合同审阅")
                
            # 继续对话
            state["dialogue_history"].append({"role": "assistant", "content": llm_response})
            return state
            
        else:
            # 普通对话，继续
            state["dialogue_history"].append({"role": "assistant", "content": llm_response})
            return state

    async def contract_reviewer_agent(self, state: AgentState) -> AgentState:
        """合同审阅智能体 - 负责合同分析和风险评估"""
        logger.info("🔍 进入合同审阅智能体节点")
        print("\n" + "="*60)
        print("🔍 合同审阅智能体开始工作")
        print("="*60)
        
        contract_path = state["contract_path"]
        logger.info(f"📄 正在审阅合同: {contract_path}")
        print(f"📄 正在审阅合同: {contract_path}")
        
        # 使用MCP工具提取合同完整内容
        contract_content = ""
        if self.mcp_client and self.tools:
            try:
                logger.info("🔧 使用MCP工具提取合同内容...")
                print("🔧 使用MCP工具提取合同内容...")
                contract_content = await self._extract_document_content(contract_path)
                logger.info(f"✅ 成功提取合同内容，长度: {len(contract_content)} 字符")
                print(f"✅ 成功提取合同内容，长度: {len(contract_content)} 字符")
                
            except Exception as e:
                logger.error(f"❌ 使用MCP工具提取内容失败: {e}")
                print(f"❌ 使用MCP工具提取内容失败: {e}")
                contract_content = f"无法通过MCP工具读取合同文件: {contract_path}"
        else:
            logger.error("❌ MCP客户端未初始化")
            print("❌ MCP客户端未初始化")
            contract_content = f"MCP客户端未初始化，无法读取合同文件: {contract_path}"

        # 构建提示词并创建消息
        try:
            prompt_file_path = Path(__file__).parent / "prompts" / "contract_reviewer_prompt.txt"
            with open(prompt_file_path, 'r', encoding='utf-8') as f:
                base_prompt = f.read()
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
            logger.info(f"✅ 成功加载提示词文件: {prompt_file_path}")
        except FileNotFoundError:
            logger.warning(f"⚠️ 提示词文件未找到，使用默认提示词")
            review_prompt = f"""
你是一个专业的合同审查律师，请对以下合同进行专业审阅。

## 输出格式要求
请严格按照以下格式输出，每个修改点必须包含四个部分：

【修改点X】- 修改点编号和标题
【原文】- 原始条款内容
【风险分析】- 法律风险分析
【修改后的内容】- 建议的修改内容

## 合同内容
```
{contract_content}
```

请开始审阅，并严格按照上述格式输出结果。
"""
        except Exception as e:
            logger.error(f"❌ 读取提示词文件失败: {e}")
            review_prompt = f"""
你是一个专业的合同审查律师，请对以下合同进行专业审阅。

## 输出格式要求
请严格按照以下格式输出，每个修改点必须包含四个部分：

【修改点X】- 修改点编号和标题
【原文】- 原始条款内容
【风险分析】- 法律风险分析
【修改后的内容】- 建议的修改内容

## 合同内容
```
{contract_content}
```

请开始审阅，并严格按照上述格式输出结果。
"""

        messages = [
            SystemMessage(content="你是一个专业的合同审查律师，请严格按照提示词要求进行合同审阅。"),
            HumanMessage(content=review_prompt)
        ]

        # 调用模型并解析结果
        response = self.llm.invoke(messages)
        review_result = response.content

        logger.info("📊 开始解析审阅结果...")
        modifications = self._parse_review_result(review_result)
        logger.info(f"📊 审阅结果分析: 识别出 {len(modifications)} 个修改点")
        print("\n📊 审阅结果分析:")
        print(f"  识别出 {len(modifications)} 个修改点")

        if modifications:
            # 基于 slots 的关键词筛选展示（不改变原始列表，仅用于预览）
            slots = state.get("slots", {}) if isinstance(state.get("slots"), dict) else {}
            keyword = (slots.get("target_clause") or slots.get("scope") or "").strip()
            filtered_indices = []
            if keyword:
                for i, mod in enumerate(modifications):
                    blob = (mod.get('original_content','') + "\n" + mod.get('risk_analysis','') + "\n" + mod.get('suggested_content','')).lower()
                    if keyword.lower() in blob:
                        filtered_indices.append(i)
            preview_indices = filtered_indices if filtered_indices else list(range(len(modifications)))

            print("\n🧭 可选修改点（预览）：")
            for j, idx in enumerate(preview_indices, 1):
                mod = modifications[idx]
                print(f"  {idx+1}. {mod.get('position', f'修改点{idx+1}')} ")

            # 处理 selection_add/selection_remove（来自多轮对话）
            add_list = slots.get("selection_add") or []
            rem_list = slots.get("selection_remove") or []
            if add_list or rem_list:
                selected = state.get("selected_mod_indices", [])
                add_zero = [i-1 for i in add_list if isinstance(i, int) and i>0 and i<=len(modifications)]
                rem_zero = [i-1 for i in rem_list if isinstance(i, int) and i>0 and i<=len(modifications)]
                selected = list({*selected, *add_zero})
                selected = [i for i in selected if i not in rem_zero]
                state["selected_mod_indices"] = selected
                print(f"✅ 已更新选择（累计）: {[i+1 for i in selected]}")
                # 从外部文件读取专业的合同审查律师提示词
        # 显示修改点详情
        if modifications:
            for i, mod in enumerate(modifications, 1):
                logger.info(f"修改点 {i}: {mod.get('position', '未知位置')}")
        else:
            logger.info("✅ 未发现需要修改的条款")
            print("  ✅ 未发现需要修改的条款")

        # 更新状态
        state["modifications"] = modifications
        state["contract_content"] = contract_content  # 保存合同内容到状态中
        state["review_data"]["contract_review"] = {
            "raw_result": review_result,
            "modifications": modifications,
            "timestamp": datetime.now().isoformat()
        }
        state["current_step"] = ""  # 回到对话循环

        # 添加审阅结果消息到对话历史
        if modifications:
            review_message = f"✅ 合同审阅完成！我发现了 {len(modifications)} 个需要关注的修改点：\n\n"
            for i, mod in enumerate(modifications[:3], 1):
                review_message += f"{i}. {mod.get('position', f'修改点{i}')}\n"
                review_message += f"   原文: {mod.get('original_content', '')[:100]}...\n"
                review_message += f"   建议: {mod.get('suggested_content', '')[:100]}...\n\n"
            
            if len(modifications) > 3:
                review_message += f"   ... 还有 {len(modifications) - 3} 个修改点\n\n"
            
            review_message += "您希望我详细解释某个修改点，还是直接应用这些修改？"
            
            logger.info(f"✅ 合同审阅智能体输出: 完成合同审阅，识别出 {len(modifications)} 个修改点")
            print(f"\n✅ 合同审阅智能体输出: 完成合同审阅，识别出 {len(modifications)} 个修改点")
        else:
            review_message = "✅ 合同审阅完成！经过仔细分析，这份合同条款基本符合法律要求，未发现需要修改的条款。"
            logger.info("✅ 合同审阅智能体输出: 完成合同审阅，未发现需要修改的条款")
            print(f"\n✅ 合同审阅智能体输出: 完成合同审阅，未发现需要修改的条款")

        # 添加到对话历史
        state["dialogue_history"].append({"role": "assistant", "content": review_message})
        
        # 保存会话状态
        self._save_session_state(state)
        
        logger.info("🔍 合同审阅智能体节点执行完成")
        return state
    
    async def document_processor_agent(self, state: AgentState) -> AgentState:
        """文档处理智能体 - 负责文档修改和报告生成"""
        logger.info("✏️ 进入文档处理智能体节点")
        print("\n" + "="*60)
        print("✏️ 文档处理智能体开始工作")
        print("="*60)
        
        contract_path = state["contract_path"]
        output_dir = state["output_dir"]
        modifications = state["modifications"]

        # 读取槽位控制
        slots = state.get("slots", {}) if isinstance(state.get("slots"), dict) else {}
        apply_changes = bool(slots.get("apply_changes", False))
        format_opts = slots.get("format") or {}
        export_opts = slots.get("export") or {}
        color = (format_opts.get("color") or "FF0000").strip()
        bold = bool(format_opts.get("bold", True))

        print(f"📄 原合同文件: {contract_path}")
        print(f"📁 输出目录: {output_dir}")
        print(f"📊 需要处理 {len(modifications)} 个修改点")
        
        try:
            # 创建修改后的文档
            modified_path = Path(output_dir) / f"modified_{Path(contract_path).name}"
            
            if self.mcp_client and self.tools:
                # 使用MCP服务进行文档修改
                logger.info("🔧 使用MCP服务修改文档")
                print("🔧 使用MCP服务修改文档")
                
                indices = state.get("selected_mod_indices", [])  # 0-based

                # 若未选择任何修改点
                if not indices:
                    print("⚠️ 未选择任何修改点，将进入预演模式，仅生成建议附件与报告，不做替换。")
                    apply_changes = False

                # 步骤1：复制文档
                await self._call_mcp_tool("copy_document", {
                    "source_filename": str(contract_path),
                    "destination_filename": str(modified_path)
                })

                if not apply_changes:
                    # 预演：在文档末尾添加建议概要，不执行替换
                    await self._call_mcp_tool("add_heading", {
                        "filename": str(modified_path),
                        "text": "拟应用的修改建议（预演）",
                        "level": 1
                    })
                    for idx in indices or range(min(5, len(modifications))):
                        mod = modifications[idx]
                        summary = (
                            f"建议 {idx+1}:\n"
                            f"原文: {mod.get('original_content','')[:200]}\n"
                            f"建议: {mod.get('suggested_content','')[:200]}\n"
                        )
                        await self._call_mcp_tool("add_paragraph", {
                            "filename": str(modified_path),
                            "text": summary,
                            "style": "Normal"
                        })
                else:
                    # 实际应用：为每个选择执行 搜索替换 + 可选格式化
                    for idx in indices:
                        if 0 <= idx < len(modifications):
                            mod = modifications[idx]
                            original = (mod.get("original_content", "") or "").strip()
                            suggested = (mod.get("suggested_content", "") or "").strip()
                            if original and suggested:
                                await self._call_mcp_tool("search_and_replace", {
                                    "filename": str(modified_path),
                                    "find_text": original,
                                    "replace_text": suggested
                                })
                                # 尝试基于全文查找定位并格式化替换后的文本（最佳努力）
                                # 这里调用 find_text_in_document 定位范围，然后 format_text 着色加粗
                                try:
                                    matches = await self._call_mcp_tool("find_text_in_document", {
                                        "filename": str(modified_path),
                                        "text_to_find": suggested,
                                        "match_case": False,
                                        "whole_word": False
                                    })
                                    if isinstance(matches, dict):
                                        match_list = matches.get("matches", [])
                                    else:
                                        match_list = matches or []
                                    for m in match_list[:3]:
                                        await self._call_mcp_tool("format_text", {
                                            "filename": str(modified_path),
                                            "paragraph_index": int(m.get("paragraph_index", 0)),
                                            "start_pos": int(m.get("start_pos", 0)),
                                            "end_pos": int(m.get("end_pos", 0)),
                                            "color": color,
                                            "bold": bold
                                        })
                                except Exception as fe:
                                    logger.warning(f"格式化替换文本失败(忽略): {fe}")

                # 可选导出 PDF
                try:
                    if isinstance(export_opts, dict) and export_opts.get("pdf") is True:
                        pdf_path = str(modified_path).rsplit('.', 1)[0] + ".pdf"
                        await self._call_mcp_tool("convert_to_pdf", {
                            "filename": str(modified_path),
                            "output_filename": pdf_path
                        })
                        print(f"📄 已导出PDF: {pdf_path}")
                except Exception as ee:
                    logger.warning(f"导出PDF失败(忽略): {ee}")
                


                
            else:
                # MCP服务不可用，抛出异常
                logger.error("❌ MCP服务不可用，无法进行文档修改")
                print("❌ MCP服务不可用，无法进行文档修改")
                raise Exception("MCP服务不可用，无法进行文档修改")
            
            # 生成格式化报告
            logger.info("📋 开始生成格式化报告...")
            print("📋 开始生成格式化报告...")
            report_path = self.generate_formatted_report(output_dir, state["review_data"])
            
            # 更新状态
            state["modified_contract_path"] = str(modified_path)
            state["report_path"] = report_path
            state["current_step"] = ""  # 回到对话循环
            
            # 构建处理结果消息
            if apply_changes:
                process_message = f"✅ 文档修改完成！\n\n"
                process_message += f"📝 修改后合同: {modified_path}\n"
                process_message += f"📄 审阅报告: {report_path}\n\n"
                process_message += f"🔍 已应用 {len(indices)} 个修改点，并在修改位置添加了标记。\n"
                process_message += f"您可以在修改后的文档中看到高亮显示的修改内容。\n\n"
                process_message += f"还需要我帮您做什么吗？"
            else:
                process_message = f"✅ 预演模式完成！\n\n"
                process_message += f"📝 预演文档: {modified_path}\n"
                process_message += f"📄 审阅报告: {report_path}\n\n"
                process_message += f"🔍 已生成修改建议概要，但未实际修改文档内容。\n"
                process_message += f"如果您确认要应用这些修改，请告诉我。\n\n"
                process_message += f"还需要我帮您做什么吗？"
            
            # 添加到对话历史
            state["dialogue_history"].append({"role": "assistant", "content": process_message})
            
            logger.info(f"📝 修改后合同: {modified_path}")
            logger.info(f"📄 审阅报告: {report_path}")
            logger.info("✅ 文档处理智能体输出: 文档修改和报告生成完成")
            print(f"📝 修改后合同: {modified_path}")
            print(f"📄 审阅报告: {report_path}")
            print("✅ 文档处理智能体输出: 文档修改和报告生成完成")
            
            # 保存会话状态
            self._save_session_state(state)
            
            logger.info("✏️ 文档处理智能体节点执行完成")
            return state
            
        except Exception as e:
            logger.error(f"❌ 文档处理失败: {e}")
            print(f"❌ 文档处理失败: {e}")
            error_message = AIMessage(content=f"文档处理失败: {str(e)}")
            state["messages"].append(error_message)
            return state
    
    def _parse_review_result(self, review_result: str) -> List[Dict[str, Any]]:
        """解析审阅结果，提取修改点信息"""
        modifications = []
        
        try:
            logger.info(f"🔍 开始解析审阅结果，原始内容长度: {len(review_result)}")
            logger.info(f"📝 审阅结果前500字符: {review_result[:500]}")
            
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
    

    
    def generate_formatted_report(self, output_dir: str, review_data: Dict[str, Any]) -> str:
        """生成格式化的检查报告"""
        logger.info("📋 开始生成格式化检查报告...")
        
        try:
            # 获取审阅数据
            contract_info = review_data.get("contract_info", {})
            contract_review = review_data.get("contract_review", {})
            modifications = contract_review.get("modifications", [])
            
            # 生成报告内容
            if modifications:
                report_content = f"""# 合同审阅报告

**审阅时间**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
**合同文件**: {contract_info.get('title', '未知')}

共识别出 {len(modifications)} 条修改建议：

"""
                
                for i, mod in enumerate(modifications, 1):
                    if isinstance(mod, dict):
                        report_content += f"""## 【修改点{i}】- {mod.get('position', f'修改点{i}')}

### 【原文】
{mod.get('original_content', '未知')}

### 【风险分析】
{mod.get('risk_analysis', '未知')}

### 【修改后的内容】
{mod.get('suggested_content', '未知')}

---
"""
                
                # 添加简短的结论
                report_content += f"""
## 总结

共提出 {len(modifications)} 条修改建议，建议根据上述分析对合同进行相应调整。

---
*本报告由AI法务合同审阅系统生成，仅供参考。具体法律意见请咨询专业律师。*
"""
            else:
                report_content = f"""# 合同审阅报告

**审阅时间**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
**合同文件**: {contract_info.get('title', '未知')}

## 审阅结果

经过专业审阅，未发现需要修改的条款。

## 总结

合同条款基本符合法律要求，无需修改。

---
*本报告由AI法务合同审阅系统生成，仅供参考。具体法律意见请咨询专业律师。*
"""
            
            # 保存报告
            report_path = Path(output_dir) / f"contract_review_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            # 同时保存JSON格式的详细数据
            json_report_path = Path(output_dir) / f"contract_review_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(json_report_path, 'w', encoding='utf-8') as f:
                json.dump(review_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 格式化报告已生成: {report_path}")
            logger.info(f"✅ 详细数据已保存: {json_report_path}")
            
            return str(report_path)
            
        except Exception as e:
            logger.error(f"❌ 生成格式化报告失败: {e}")
            return ""
    
    async def review_contract(self, contract_path: str, output_dir: str = "output",user_question:str = "") -> Dict[str, Any]:
        """审阅合同 - 使用多智能体系统"""
        logger.info("🚀 开始多智能体合同审阅流程")
        print("\n" + "🚀" + "="*58)
        print("🚀 开始多智能体合同审阅流程")
        print("🚀" + "="*58)
        
        # 确保输出目录存在
        Path(output_dir).mkdir(exist_ok=True)
        
        # 初始化MCP客户端
        logger.info("🔧 初始化MCP客户端...")
        print("🔧 初始化MCP客户端...")
        mcp_available = await self.initialize_mcp_client()
        
        if mcp_available:
            logger.info("✅ MCP客户端初始化成功")
            print("✅ MCP客户端初始化成功")
        else:
            logger.error("❌ MCP客户端初始化失败")
            print("❌ MCP客户端初始化失败")
        
        # 创建多智能体图
        logger.info("🏗️ 创建多智能体图...")
        print("🏗️ 创建多智能体图...")
        self.create_multi_agent_graph()
        logger.info("✅ 多智能体图创建成功")
        print("✅ 多智能体图创建成功")
        
        try:
            # 初始化状态
            initial_state = {
                "messages": [],
                "contract_path": contract_path,
                "output_dir": output_dir,
                "review_data": {},
                "current_step": "",
                "modifications": [],
                "modified_contract_path": "",
                "report_path": "",
                "dialogue_history": [{"role": "user", "content": user_question}] if user_question else[],#test
                "user_input_required": True,
                "selected_mod_indices": []
            }
            
            logger.info("🔄 开始执行多智能体工作流...")
            print("\n🔄 开始执行多智能体工作流...")
            
            # 执行多智能体工作流
            config = {"configurable": {"thread_id": f"multi_agent_review_{datetime.now().strftime('%Y%m%d_%H%M%S')}"},
            "recursion_limit": 50
            }
            
            result = await self.graph.ainvoke(initial_state, config=config)
            
            logger.info("🎉 多智能体工作流执行完成")
            print("\n" + "🎉" + "="*58)
            print("🎉 多智能体工作流执行完成")
            print("🎉" + "="*58)
            
            # 生成结果
            final_result = {
                "success": True,
                "contract_path": contract_path,
                "output_dir": output_dir,
                "modified_contract_path": result.get("modified_contract_path", ""),
                "report_path": result.get("report_path", ""),
                "review_data": result.get("review_data", {}),
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info("✅ 多智能体合同审阅完成")
            print("✅ 多智能体合同审阅完成")
            return final_result
            
        except Exception as e:
            print(f"❌ 多智能体合同审阅失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "contract_path": contract_path,
                "output_dir": output_dir
            }

async def main():
    """主函数 - 支持多轮对话的合同审阅系统"""
    print("🏛️ 多智能体法务合同审阅系统")
    print("=" * 50)
    
    # 检查环境变量
    if not DEEPSEEK_API_KEY:
        print("❌ 请设置DEEPSEEK_API_KEY环境变量")
        return
    
    # 检查ReAct Agent可用性
    if not REACT_AGENT_AVAILABLE:
        print("❌ 当前环境不支持ReAct Agent")
        print("请使用以下命令切换到base环境:")
        print("conda activate base")
        return
    
    # 创建多智能体审阅系统
    review_system = MultiAgentContractReviewSystem()
    
    # 初始化MCP客户端
    print("🔧 初始化MCP客户端...")
    mcp_available = await review_system.initialize_mcp_client()
    if not mcp_available:
        print("❌ MCP客户端初始化失败")
        return
    
    # 创建多智能体图
    review_system.create_multi_agent_graph()
    
    # 使用绝对路径
    current_dir = Path.cwd()
    data_dir = current_dir / "data"
    output_dir = current_dir / "output"
    
    if not data_dir.exists():
        print(f"❌ data目录不存在: {data_dir}")
        return
    
    contract_files = list(data_dir.glob("*.docx"))
    if not contract_files:
        print("❌ 未找到合同文件")
        return
    
    print("📄 可用的合同文件:")
    for i, file in enumerate(contract_files, 1):
        print(f"  {i}. {file.name}")
        print(f"     路径: {file.absolute()}")
    
    try:
        choice = int(input("\n请选择要审阅的合同文件 (输入序号): ")) - 1
        if 0 <= choice < len(contract_files):
            contract_path = str(contract_files[choice].absolute())
        else:
            print("❌ 无效选择")
            return
    except ValueError:
        print("❌ 请输入有效数字")
        return

    print(f"\n📋 选择的合同文件: {contract_path}")
    print(f"📁 输出目录: {output_dir.absolute()}")
    
    # 生成会话ID
    session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # 初始化状态
    initial_state = {
        "messages": [],
        "contract_path": contract_path,
        "output_dir": str(output_dir),
        "review_data": {},
        "current_step": "",
        "modifications": [],
        "modified_contract_path": "",
        "report_path": "",
        "contract_content": "",
        "dialogue_history": [],
        "user_input_required": True,
        "selected_mod_indices": [],
        "intent": "",
        "slots": {},
        "confirmed_scope": "",
        "session_id": session_id,
        "has_file": True  # 已选择文件
    }
    
    print("\n" + "🔄" + "="*58)
    print("🔄 多智能体审阅流程说明")
    print("🔄" + "="*58)
    print("🎯 监督者智能体 - 协调整个审阅流程")
    print("🔍 合同审阅智能体 - 负责合同分析和风险评估")
    print("✏️ 文档处理智能体 - 负责文档修改和报告生成")
    print("="*60)
    
    # 多轮对话循环
    try:
        while True:
            # 执行多智能体工作流
            config = {
                "configurable": {"thread_id": session_id},
                "recursion_limit": 50
            }
            
            result = await review_system.graph.ainvoke(initial_state, config=config)
            
            # 检查是否结束
            if result.get("current_step") == "completed":
                print("\n👋 感谢使用智能合同审阅系统，再见！")
                break
            
            # 更新状态用于下一轮对话
            initial_state = result
            
    except KeyboardInterrupt:
        print("\n\n👋 用户中断，感谢使用智能合同审阅系统！")
    except Exception as e:
        print(f"\n❌ 系统错误: {e}")
        logger.error(f"系统错误: {e}")

# 创建系统实例
review_system = MultiAgentContractReviewSystem()

# API端点
@app.on_event("startup")
async def startup_event():
    """应用启动时初始化系统"""
    await review_system.initialize_system()

@app.post("/api/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    session_id: str = Form(None)
):
    """上传合同文档"""
    try:
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # 检查文件类型
        if not file.filename.endswith('.docx'):
            raise HTTPException(status_code=400, detail="只支持.docx格式的文件")
        
        # 保存文件
        filename = f"{session_id}_{file.filename}"
        file_path = review_system.upload_dir / filename
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # 更新会话
        session = review_system.get_or_create_session(session_id)
        session["contract_path"] = str(file_path)
        session["document_id"] = filename
        
        return UploadResponse(
            success=True,
            message="文件上传成功",
            session_id=session_id,
            document_id=filename
        )
        
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_assistant(request: ChatRequest):
    """与助手对话"""
    try:
        if not request.session_id:
            request.session_id = str(uuid.uuid4())
        
        result = await review_system.process_chat_message(
            request.message, 
            request.session_id, 
            request.action
        )
        
        return ChatResponse(**result)
        
    except Exception as e:
        logger.error(f"聊天处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"聊天处理失败: {str(e)}")

@app.get("/api/download/{session_id}/{file_type}")
async def download_file(session_id: str, file_type: str):
    """下载文件"""
    try:
        session = review_system.get_or_create_session(session_id)
        
        if file_type == "modified":
            file_path = session.get("modified_contract_path")
            if not file_path or not Path(file_path).exists():
                raise HTTPException(status_code=404, detail="修改后的文档不存在")
            return FileResponse(
                file_path, 
                filename=f"modified_contract_{session_id}.docx",
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        
        elif file_type == "report":
            file_path = session.get("report_path")
            if not file_path or not Path(file_path).exists():
                raise HTTPException(status_code=404, detail="报告不存在")
            return FileResponse(
                file_path, 
                filename=f"contract_report_{session_id}.md",
                media_type="text/markdown"
            )
        
        else:
            raise HTTPException(status_code=400, detail="不支持的文件类型")
            
    except Exception as e:
        logger.error(f"文件下载失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件下载失败: {str(e)}")

@app.get("/api/session/{session_id}")
async def get_session_info(session_id: str):
    """获取会话信息"""
    try:
        session = review_system.get_or_create_session(session_id)
        return {
            "session_id": session_id,
            "has_contract": bool(session.get("contract_path")),
            "modifications_count": len(session.get("modifications", [])),
            "has_modified_document": bool(session.get("modified_contract_path")),
            "has_report": bool(session.get("report_path")),
            "created_at": session.get("created_at")
        }
    except Exception as e:
        logger.error(f"获取会话信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取会话信息失败: {str(e)}")

@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
