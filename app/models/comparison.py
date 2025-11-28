"""
合同比对任务模型
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, TIMESTAMP, Text

from app.core.mysql_db import Base


class ComparisonTask(Base):
    """
    合同比对任务表
    """
    __tablename__ = "comparison_task"

    id = Column(Integer, primary_key=True, comment="比对任务ID")
    session_id = Column(Integer, nullable=False, comment="关联会话ID")
    user_id = Column(Integer, nullable=False, comment="发起用户ID")
    standard_file_id = Column(Integer, nullable=False, comment="标准文档ID")
    comparison_file_id = Column(Integer, nullable=False, comment="比对文档ID")
    status = Column(String(32), default="pending", comment="任务状态")
    diff_summary = Column(Text, comment="差异摘要JSON")
    diff_result = Column(Text, comment="差异详情JSON")
    created_at = Column(TIMESTAMP, default=datetime.now, comment="创建时间")
    completed_at = Column(TIMESTAMP, nullable=True, comment="完成时间")

    def dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "standard_file_id": self.standard_file_id,
            "comparison_file_id": self.comparison_file_id,
            "status": self.status,
            "diff_summary": self.diff_summary,
            "diff_result": self.diff_result,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

