"""
@Project ：Contract_Review_backend-Py 
@File    ：contract.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/22 15:24 
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, TIMESTAMP

from app.core.mysql_db import Base

class ContractFile(Base):
    """
    合同文件表
    """
    __tablename__ = "contract_file"

    id = Column(Integer, primary_key=True,comment="合同ID")
    user_id = Column(Integer,comment="上传者")
    title = Column(String(256),comment="合同标题")
    file_path = Column(String(512),comment="存储路径")
    file_type = Column(String(16),comment="文件类型（pdf/docx）")
    upload_time = Column(TIMESTAMP, default=datetime.now, comment="上传时间")
    status = Column(String(32),default="uploaded",comment="状态（uploaded/parsed/reviewed）")
