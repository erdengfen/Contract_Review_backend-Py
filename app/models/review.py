"""
@Project ：Contract_Review_backend-Py 
@File    ：review_task.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/22 15:31 
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, TIMESTAMP,Text

from app.core.mysql_db import Base

class ReviewTask(Base):
    """
    审查任务表
    """
    __tablename__ = "review_task"

    id = Column(Integer, primary_key=True,comment="任务ID")
    session_id = Column(Integer,comment="会话ID")
    contract_id = Column(Integer,comment="所属文件")
    user_id = Column(Integer,comment="发起用户")
    stance = Column(String(32),comment="审查立场")
    intensity = Column(String(32),comment="审查尺度")
    description = Column(Text,comment="审查需求描述")
    status = Column(String(32),comment="状态")
    created_at = Column(TIMESTAMP, default=datetime.now, comment="创建时间")
    completed_at = Column(TIMESTAMP, default=datetime.now, comment="完成时间")

class ReviewResult(Base):
    """
    审查结果表
    """
    __tablename__ = "review_result"

    id = Column(Integer, primary_key=True,comment="结果ID")
    session_id = Column(Integer,comment="会话ID")
    task_id = Column(Integer,comment="任务ID")
    overall_risk = Column(String(16),comment="Overall Risk")
    summary = Column(Text,comment="Summary")
    suggestion = Column(Text,comment="Suggestion")
    created_at = Column(TIMESTAMP, default=datetime.now, comment="创建时间")

class RiskItem(Base):
    """
    风险项表
    """
    __tablename__ = "risk_item"

    id = Column(Integer, primary_key=True,comment="风险项ID")
    result_id = Column(Integer,comment="结果ID")
    clause_text = Column(Text,comment="条款内容")
    risk_type = Column(String(64),comment="风险类型")
    risk_level = Column(String(16),comment="风险等级")
    suggestion = Column(Text,comment="建议")


