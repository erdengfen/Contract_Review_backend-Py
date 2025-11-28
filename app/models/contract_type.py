"""
@Project ：Contract_Review_backend-Py 
@File    ：contract_type.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/31 11:48 
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, TIMESTAMP

from app.core.mysql_db import Base

class ContractType(Base):
    """
    合同类型表
    """

    __tablename__ = "contract_type"

    id = Column(Integer, primary_key=True,comment="合同类型ID")
    name = Column(String(64),comment="合同类型名称")
    description = Column(String(256),comment="合同类型描述")
    is_active = Column(Integer, default=1, comment="是否激活")
    create_time = Column(TIMESTAMP, default=datetime.now, comment="创建时间")
    update_time = Column(TIMESTAMP, default=datetime.now, onupdate=datetime.now, comment="更新时间")
