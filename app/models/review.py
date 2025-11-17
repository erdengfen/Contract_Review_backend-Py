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
    type = Column(String(32),comment="类型: 审查:review, 校验:validate,比对:compare")
    file_id = Column(Integer,comment="所属文件")
    user_id = Column(Integer,comment="发起用户")
    stance = Column(String(32),comment="审查立场")
    intensity = Column(String(32),comment="审查尺度")
    description = Column(Text,comment="审查需求描述")
    status = Column(String(32),comment="状态: pending:待处理, completed:已完成, failed:处理失败")
    created_at = Column(TIMESTAMP, default=datetime.now, comment="创建时间")
    completed_at = Column(TIMESTAMP, default=datetime.now, comment="完成时间")

    def dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "file_id": self.file_id,
            "user_id": self.user_id,
            "stance": self.stance,
            "intensity": self.intensity,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

class ReviewResult(Base):
    """
    审查结果表
    """
    __tablename__ = "review_result"

    id = Column(Integer, primary_key=True,comment="结果ID")
    session_id = Column(Integer,comment="会话ID")
    task_id = Column(Integer,comment="任务ID")
    index = Column(Integer,comment="结果索引")
    original_content = Column(Text,comment="原始文本")
    risk_analysis = Column(Text,comment="风险分析")
    risk_level = Column(String(16),comment="风险等级")
    suggested_content = Column(Text,comment="建议内容")
    is_accepted = Column(Integer, default=0, comment="是否接受建议")
    created_at = Column(TIMESTAMP, default=datetime.now, comment="创建时间")

    def dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "index": self.index,
            "original_content": self.original_content,
            "risk_analysis": self.risk_analysis,
            "risk_level": self.risk_level,
            "suggested_content": self.suggested_content,
            "is_accepted": self.is_accepted,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }