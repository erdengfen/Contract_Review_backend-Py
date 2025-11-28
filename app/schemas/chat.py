from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime




# ---------------------
class ChatRequest(BaseModel):
    """
    合同聊天请求
    """
    session_id: Optional[int] = Field(None, description="会话ID（可选，用于继续会话）")
    content: Optional[str] = Field(None, description="消息内容（可选，用于创建消息）")
    parent_id: Optional[int] = Field(None, description="父消息ID（可选，用于多轮或修正）")
