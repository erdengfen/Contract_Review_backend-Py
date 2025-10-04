"""
文档处理服务
"""
import logging
from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path

from ..utils.mcp_client import MCPClient

logger = logging.getLogger(__name__)

class DocumentProcessorService:
    """文档处理服务"""
    
    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client
    
    async def modify_document(self, contract_path: str, modifications: List[Dict[str, Any]], 
                            selected_indices: List[int], output_dir: str) -> Dict[str, str]:
        """执行文档修改"""
        try:
            # 创建修改后的文档
            modified_filename = f"modified_{Path(contract_path).name}"
            modified_path = Path(output_dir) / modified_filename
            
            # 复制文档
            await self.mcp_client.call_tool("copy_document", {
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
                        await self.mcp_client.call_tool("search_and_replace", {
                            "filename": str(modified_path),
                            "find_text": original,
                            "replace_text": suggested
                        })
                        
                        # 格式化修改后的文本
                        try:
                            matches = await self.mcp_client.call_tool("find_text_in_document", {
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
                                await self.mcp_client.call_tool("format_text", {
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
            report_path = self._generate_report(contract_path, str(modified_path), modifications, output_dir)
            
            return {
                "modified_contract_path": str(modified_path),
                "report_path": report_path
            }
            
        except Exception as e:
            logger.error(f"❌ 文档修改失败: {e}")
            return {"modified_contract_path": "", "report_path": ""}
    
    def _generate_report(self, contract_path: str, modified_path: str, 
                        modifications: List[Dict[str, Any]], output_dir: str) -> str:
        """生成审阅报告"""
        try:
            contract_name = Path(contract_path).stem
            
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
            report_path = Path(output_dir) / f"contract_review_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            return str(report_path)
            
        except Exception as e:
            logger.error(f"❌ 生成报告失败: {e}")
            return ""
