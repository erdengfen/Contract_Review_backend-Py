"""
MCP客户端工具
"""
import logging
from typing import Any, Dict, List
from langchain_mcp_adapters.client import MultiServerMCPClient
from ..core.config import MCP_SERVER_URL

logger = logging.getLogger(__name__)

class MCPClient:
    """MCP客户端封装"""
    
    def __init__(self):
        self.client = None
        self.tools = []
    
    async def initialize(self) -> bool:
        """初始化MCP客户端"""
        try:
            self.client = MultiServerMCPClient({
                "office-word-mcp": {
                    "url": MCP_SERVER_URL,
                    "transport": "streamable_http",
                }
            })
            
            self.tools = await self.client.get_tools()
            logger.info(f"✅ MCP客户端初始化成功，获取到 {len(self.tools)} 个工具")
            return True
            
        except Exception as e:
            logger.error(f"❌ MCP客户端初始化失败: {e}")
            return False
    
    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        """调用MCP工具"""
        try:
            tool = next((t for t in self.tools if t.name == tool_name), None)
            if tool:
                return await tool.ainvoke(arguments)
            else:
                raise Exception(f"找不到工具: {tool_name}")
        except Exception as e:
            logger.error(f"调用MCP工具 {tool_name} 失败: {e}")
            raise
    
    async def extract_document_content(self, file_path: str) -> str:
        """提取文档内容"""
        try:
            result = await self.call_tool("get_document_text", {"filename": file_path})
            if result:
                content = str(result)
                logger.info(f"✅ 成功提取文档内容，长度: {len(content)} 字符")
                return content
            else:
                raise Exception("工具返回空结果")
        except Exception as e:
            logger.error(f"❌ 提取文档内容失败: {e}")
            raise Exception(f"无法提取文档内容: {e}")
