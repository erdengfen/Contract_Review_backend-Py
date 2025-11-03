"""
@Project ：Contract_Review_backend-Py 
@File    ：session.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/22 15:27 
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, TIMESTAMP,Text

from app.core.mysql_db import Base


from enum import Enum

class SessionTypeEnum(str, Enum):
    CHAT = "chat" # 普通会话
    REVIEW = "review" # 合同审阅会话


class Session(Base):
    """
    会话表
    """
    __tablename__ = "session"

    id = Column(Integer, primary_key=True,comment="会话ID")
    contract_id = Column(Integer,comment="所属文件")
    user_id = Column(Integer,comment="发起用户")
    title = Column(String(256),comment="会话主题")
    session_type = Column(String(16),comment="会话类型")
    created_at = Column(TIMESTAMP, default=datetime.now, comment="创建时间")
    updated_at = Column(TIMESTAMP, default=datetime.now, comment="更新时间")

class Message(Base):
    """
    消息表
    """
    __tablename__ = "message"
    id = Column(Integer, primary_key=True,comment="消息ID")
    session_id = Column(Integer,comment="会话ID")
    role = Column(String(16),comment="角色")
    content = Column(Text,comment="消息内容")
    parent_id = Column(Integer, nullable=True, comment="父消息ID（可选）") # 退回修改重新会话兼容
    message_index = Column(Integer, nullable=True, comment="消息顺序索引")
    created_at = Column(TIMESTAMP, default=datetime.now, comment="创建时间")
