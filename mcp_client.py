#!/usr/bin/env python3
"""
MCP客户端模块 - 用于与Word文档处理服务器通信
基于Office-Word-MCP-Server的完整功能实现
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import aiohttp
from pydantic import BaseModel
import os

logger = logging.getLogger(__name__)

class MCPClient:
    """MCP客户端 - Streamable HTTP模式"""
    def __init__(self, server_url: str = None):
        self.server_url = server_url or os.getenv('MCP_SERVER_URL', 'http://127.0.0.1:8080/mcp/')
        self.session: Optional[aiohttp.ClientSession] = None
        self.session_id: Optional[str] = None
        self.initialized = False

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        await self._initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def _initialize(self):
        if self.initialized:
            return
        try:
            init_payload = {
                "jsonrpc": "2.0",
                "id": "init",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "contract-review-client", "version": "1.0.0"}
                }
            }
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"
            }
            async with self.session.post(self.server_url, json=init_payload, headers=headers) as resp:
                if resp.status == 200:
                    self.session_id = resp.headers.get("mcp-session-id")
                    logger.info(f"获取到session ID: {self.session_id}")
                    self.initialized = True
                else:
                    text = await resp.text()
                    logger.error(f"MCP初始化失败: {resp.status} - {text}")
                    raise Exception(f"MCP初始化失败: {resp.status}")
        except Exception as e:
            logger.error(f"MCP初始化失败: {e}")
            raise

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        if not self.session:
            raise RuntimeError("MCP客户端未初始化，请使用异步上下文管理器")
        if not self.initialized or not self.session_id:
            await self._initialize()
        tool_payload = {
            "jsonrpc": "2.0",
            "id": f"tool-{tool_name}",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "mcp-session-id": self.session_id
        }
        async with self.session.post(self.server_url, json=tool_payload, headers=headers) as resp:
            if resp.status == 200:
                content_type = resp.headers.get('content-type', '')
                if 'text/event-stream' in content_type:
                    # 读取流式响应
                    async for line in resp.content:
                        line = line.decode('utf-8').strip()
                        if line.startswith('data: '):
                            try:
                                data = json.loads(line[6:])
                                if data.get('id') == f"tool-{tool_name}":
                                    if "error" in data:
                                        logger.error(f"工具调用错误: {data['error']}")
                                        raise Exception(f"工具调用错误: {data['error']}")
                                    return data.get("result", data)
                            except json.JSONDecodeError:
                                continue
                    return {}
                else:
                    result = await resp.json()
                    if "error" in result:
                        logger.error(f"工具调用错误: {result['error']}")
                        raise Exception(f"工具调用错误: {result['error']}")
                    return result.get("result", result)
            else:
                text = await resp.text()
                logger.error(f"MCP工具调用失败: {resp.status} - {text}")
                raise Exception(f"MCP工具调用失败: {resp.status}")

    async def get_document_text(self, filename: str) -> str:
        try:
            abs_filename = str(Path(filename).resolve())
            result = await self.call_tool("get_document_text", {"filename": abs_filename})
            if isinstance(result, str):
                return result
            return result.get("content", "")
        except Exception as e:
            logger.error(f"获取文档文本失败: {e}")
            return ""

    async def get_document_info(self, filename: str) -> Dict[str, Any]:
        try:
            abs_filename = str(Path(filename).resolve())
            result = await self.call_tool("get_document_info", {"filename": abs_filename})
            if isinstance(result, str):
                try:
                    return json.loads(result)
                except json.JSONDecodeError:
                    return {"info": result}
            return result if isinstance(result, dict) else {}
        except Exception as e:
            logger.error(f"获取文档信息失败: {e}")
            return {}

    async def search_and_replace(self, filename: str, search_text: str, replace_text: str) -> bool:
        try:
            abs_filename = str(Path(filename).resolve())
            result = await self.call_tool("search_and_replace", {
                "filename": abs_filename,
                "find_text": search_text,
                "replace_text": replace_text
            })
            return result.get("success", False)
        except Exception as e:
            logger.error(f"搜索替换失败: {e}")
            return False

    async def format_text(self, filename: str, paragraph_index: int, start_pos: int, end_pos: int,
                         color: str = "FF0000", bold: bool = True) -> bool:
        try:
            abs_filename = str(Path(filename).resolve())
            result = await self.call_tool("format_text", {
                "filename": abs_filename,
                "paragraph_index": paragraph_index,
                "start_pos": start_pos,
                "end_pos": end_pos,
                "color": color,
                "bold": bold
            })
            return result.get("success", False)
        except Exception as e:
            logger.error(f"格式化文本失败: {e}")
            return False

    async def add_paragraph(self, filename: str, text: str, style: str = "Normal") -> bool:
        try:
            abs_filename = str(Path(filename).resolve())
            result = await self.call_tool("add_paragraph", {
                "filename": abs_filename,
                "text": text,
                "style": style
            })
            return result.get("success", False)
        except Exception as e:
            logger.error(f"添加段落失败: {e}")
            return False

    async def add_heading(self, filename: str, text: str, level: int = 1) -> bool:
        try:
            abs_filename = str(Path(filename).resolve())
            result = await self.call_tool("add_heading", {
                "filename": abs_filename,
                "text": text,
                "level": level
            })
            return result.get("success", False)
        except Exception as e:
            logger.error(f"添加标题失败: {e}")
            return False

    async def copy_document(self, source_filename: str, destination_filename: str) -> bool:
        try:
            abs_source = str(Path(source_filename).resolve())
            abs_dest = str(Path(destination_filename).resolve())
            result = await self.call_tool("copy_document", {
                "source_filename": abs_source,
                "destination_filename": abs_dest
            })
            return result.get("success", False)
        except Exception as e:
            logger.error(f"复制文档失败: {e}")
            return False

    async def create_document(self, filename: str, title: str = None, author: str = None) -> bool:
        try:
            abs_filename = str(Path(filename).resolve())
            result = await self.call_tool("create_document", {
                "filename": abs_filename,
                "title": title,
                "author": author
            })
            return result.get("success", False)
        except Exception as e:
            logger.error(f"创建文档失败: {e}")
            return False

    async def find_text_in_document(self, filename: str, text_to_find: str, 
                                   match_case: bool = True, whole_word: bool = False) -> List[Dict[str, Any]]:
        try:
            abs_filename = str(Path(filename).resolve())
            result = await self.call_tool("find_text_in_document", {
                "filename": abs_filename,
                "text_to_find": text_to_find,
                "match_case": match_case,
                "whole_word": whole_word
            })
            return result.get("matches", [])
        except Exception as e:
            logger.error(f"查找文本失败: {e}")
            return []

    async def get_paragraph_text_from_document(self, filename: str, paragraph_index: int) -> str:
        try:
            abs_filename = str(Path(filename).resolve())
            result = await self.call_tool("get_paragraph_text_from_document", {
                "filename": abs_filename,
                "paragraph_index": paragraph_index
            })
            return result.get("text", "")
        except Exception as e:
            logger.error(f"获取段落文本失败: {e}")
            return ""

class WordDocumentProcessor:
    """Word文档处理器 - 高级文档操作"""
    
    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client
    
    async def extract_contract_content(self, file_path: str) -> str:
        """提取合同内容"""
        try:
            logger.info(f"正在提取合同内容: {file_path}")
            
            # 检查文件是否存在
            if not Path(file_path).exists():
                logger.error(f"文件不存在: {file_path}")
                return ""
            
            # 获取文档文本
            content = await self.mcp_client.get_document_text(file_path)
            
            if not content:
                logger.warning("文档内容为空")
                return ""
            
            logger.info(f"成功提取合同内容，长度: {len(content)} 字符")
            return content
            
        except Exception as e:
            logger.error(f"提取合同内容失败: {e}")
            return ""
    
    async def highlight_risks(self, file_path: str, risk_points: List[Dict[str, Any]]) -> str:
        """在文档中标红风险点"""
        try:
            logger.info(f"开始标红风险点，共 {len(risk_points)} 个")
            
            # 创建标红版本的文件名
            base_path = Path(file_path)
            highlighted_path = base_path.parent / f"highlighted_{base_path.name}"
            
            # 复制原文档
            success = await self.mcp_client.copy_document(str(file_path), str(highlighted_path))
            if not success:
                logger.error("复制文档失败")
                return ""
            
            # 为每个风险点进行标红
            for i, risk in enumerate(risk_points):
                try:
                    risk_text = risk.get("text", "")
                    risk_level = risk.get("level", "medium")
                    risk_description = risk.get("description", "")
                    
                    if not risk_text:
                        continue
                    
                    # 查找风险文本在文档中的位置
                    matches = await self.mcp_client.find_text_in_document(
                        str(highlighted_path), risk_text, match_case=False
                    )
                    
                    for match in matches:
                        paragraph_index = match.get("paragraph_index", 0)
                        start_pos = match.get("start_pos", 0)
                        end_pos = match.get("end_pos", len(risk_text))
                        
                        # 根据风险等级选择颜色
                        color = {
                            "high": "FF0000",      # 红色
                            "medium": "FF6600",    # 橙色
                            "low": "FFCC00"        # 黄色
                        }.get(risk_level, "FF0000")
                        
                        # 格式化文本（标红）
                        await self.mcp_client.format_text(
                            str(highlighted_path),
                            paragraph_index,
                            start_pos,
                            end_pos,
                            color=color,
                            bold=True
                        )
                    
                    logger.info(f"已标红风险点 {i+1}: {risk_text[:50]}...")
                    
                except Exception as e:
                    logger.error(f"标红风险点 {i+1} 失败: {e}")
                    continue
            
            logger.info(f"风险标红完成: {highlighted_path}")
            return str(highlighted_path)
            
        except Exception as e:
            logger.error(f"标红风险点失败: {e}")
            return ""
    
    async def add_modification_suggestions(self, file_path: str, 
                                         modifications: List[Dict[str, Any]]) -> bool:
        """添加修改建议到文档"""
        try:
            logger.info(f"添加修改建议，共 {len(modifications)} 个")
            
            # 在文档末尾添加修改建议章节
            await self.mcp_client.add_heading(file_path, "修改建议", level=1)
            
            for i, modification in enumerate(modifications):
                try:
                    suggestion = modification.get("suggestion", "")
                    priority = modification.get("priority", "medium")
                    reason = modification.get("reason", "")
                    
                    if not suggestion:
                        continue
                    
                    # 添加建议标题
                    priority_text = {
                        "high": "高优先级",
                        "medium": "中优先级", 
                        "low": "低优先级"
                    }.get(priority, "中优先级")
                    
                    await self.mcp_client.add_heading(
                        file_path, 
                        f"建议 {i+1} ({priority_text})", 
                        level=2
                    )
                    
                    # 添加建议内容
                    await self.mcp_client.add_paragraph(file_path, suggestion)
                    
                    # 添加建议原因
                    if reason:
                        await self.mcp_client.add_paragraph(file_path, f"原因: {reason}")
                    
                    # 添加分隔符
                    await self.mcp_client.add_paragraph(file_path, "")
                    
                except Exception as e:
                    logger.error(f"添加修改建议 {i+1} 失败: {e}")
                    continue
            
            logger.info("修改建议添加完成")
            return True
            
        except Exception as e:
            logger.error(f"添加修改建议失败: {e}")
            return False
    
    async def create_review_report(self, original_file: str, 
                                 contract_analysis: Dict[str, Any],
                                 risk_assessment: Dict[str, Any],
                                 modifications: List[Dict[str, Any]]) -> str:
        """创建审阅报告"""
        try:
            logger.info("开始创建审阅报告")
            
            # 创建报告文件名
            base_path = Path(original_file)
            report_path = base_path.parent / f"contract_review_report_{base_path.stem}.docx"
            
            # 创建新文档
            success = await self.mcp_client.create_document(
                str(report_path),
                title="合同审阅报告",
                author="AI法务助手"
            )
            
            if not success:
                logger.error("创建报告文档失败")
                return ""
            
            # 添加报告标题
            await self.mcp_client.add_heading(str(report_path), "合同审阅报告", level=1)
            
            # 添加执行摘要
            await self.mcp_client.add_heading(str(report_path), "执行摘要", level=2)
            summary = f"""
            本报告对合同文件 "{base_path.name}" 进行了全面的法务审阅。
            
            审阅时间: {contract_analysis.get('review_time', '未知')}
            合同类型: {contract_analysis.get('contract_type', '未知')}
            主要风险等级: {risk_assessment.get('overall_risk_level', '未知')}
            发现风险点数量: {len(risk_assessment.get('risk_points', []))}
            建议修改数量: {len(modifications)}
            """
            await self.mcp_client.add_paragraph(str(report_path), summary)
            
            # 添加合同概况
            await self.mcp_client.add_heading(str(report_path), "合同概况", level=2)
            contract_info = contract_analysis.get('contract_info', {})
            contract_summary = f"""
            合同名称: {contract_info.get('title', '未知')}
            合同金额: {contract_info.get('amount', '未知')}
            合同期限: {contract_info.get('duration', '未知')}
            主要条款: {', '.join(contract_info.get('main_terms', []))}
            """
            await self.mcp_client.add_paragraph(str(report_path), contract_summary)
            
            # 添加风险评估
            await self.mcp_client.add_heading(str(report_path), "风险评估", level=2)
            
            risk_points = risk_assessment.get('risk_points', [])
            for i, risk in enumerate(risk_points):
                risk_text = f"""
                风险点 {i+1}:
                - 风险内容: {risk.get('text', '未知')}
                - 风险等级: {risk.get('level', '未知')}
                - 风险描述: {risk.get('description', '未知')}
                - 建议措施: {risk.get('suggestion', '未知')}
                """
                await self.mcp_client.add_paragraph(str(report_path), risk_text)
            
            # 添加修改建议
            await self.mcp_client.add_heading(str(report_path), "修改建议", level=2)
            
            for i, modification in enumerate(modifications):
                mod_text = f"""
                建议 {i+1}:
                - 优先级: {modification.get('priority', '未知')}
                - 建议内容: {modification.get('suggestion', '未知')}
                - 修改原因: {modification.get('reason', '未知')}
                """
                await self.mcp_client.add_paragraph(str(report_path), mod_text)
            
            # 添加结论
            await self.mcp_client.add_heading(str(report_path), "结论和建议", level=2)
            conclusion = f"""
            基于以上分析，本合同的整体风险等级为 {risk_assessment.get('overall_risk_level', '未知')}。
            
            主要建议:
            1. 重点关注高风险条款，建议进行相应修改
            2. 完善合同条款的明确性和可执行性
            3. 加强违约责任和争议解决机制
            4. 建议在签署前进行进一步的法律咨询
            
            本报告仅供参考，具体法律意见请咨询专业律师。
            """
            await self.mcp_client.add_paragraph(str(report_path), conclusion)
            
            logger.info(f"审阅报告创建完成: {report_path}")
            return str(report_path)
            
        except Exception as e:
            logger.error(f"创建审阅报告失败: {e}")
            return ""

async def test_mcp_client():
    """测试MCP客户端功能"""
    try:
        async with MCPClient() as client:
            processor = WordDocumentProcessor(client)
            
            # 测试文档信息获取
            test_file = "data/校园主页升级改版服务合同.docx"
            if Path(test_file).exists():
                info = await client.get_document_info(test_file)
                print(f"文档信息: {info}")
                
                content = await processor.extract_contract_content(test_file)
                print(f"文档内容长度: {len(content)}")
                print(f"内容预览: {content[:200]}...")
            else:
                print(f"测试文件不存在: {test_file}")
                
    except Exception as e:
        print(f"测试失败: {e}")

if __name__ == "__main__":
    asyncio.run(test_mcp_client()) 