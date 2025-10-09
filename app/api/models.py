"""
API请求/响应模型
"""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

"""
会话 ID（session_id）的作用：
绑定上下文：把同一轮交互的上传文件、对话历史、审阅结果等状态关联在一起，保证多次请求之间有“记忆”。
定位文件：上传后的 .docx 会以 session_id_文件名.docx 命名，并在会话里记录 contract_path，后续审阅/修改都用它。
路由返回：下载链接里会带上 session_id（如 /api/download/{session_id}/modified），用于准确取回该会话生成的文件。
多会话并行：不同 session_id 互不干扰，支持多人/多任务并发。
无状态补偿：HTTP 本身无状态，session_id 充当服务端内存状态的“钥匙”
"""

# 请求体模型（用户消息、会话 ID、动作类型）。
class ChatRequest(BaseModel):
    message: Optional[str] = "审阅"
    session_id: str
    action: Optional[str] = "chat"  # chat, review, modify, export
    role: Optional[str] = None

# 响应体模型（响应消息、会话 ID、动作类型、修改建议、修改后的文档 URL、报告 URL）。
class ChatResponse(BaseModel):
    response: str
    session_id: str
    action: str
    modifications: Optional[List[Dict[str, Any]]] = None
    modified_document_url: Optional[str] = None
    report_url: Optional[str] = None

# 上传响应体模型（成功标志、消息、会话 ID、文档 ID）。
class UploadResponse(BaseModel):
    success: bool
    message: str
    session_id: str
    document_id: str
    party_a: Optional[str] = None #甲方名称
    party_b: Optional[str] = None #乙方名称
