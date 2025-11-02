"""
@Project ：Contract_Review_backend-Py 
@File    ：model_configs.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/11/2 10:55 
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, TIMESTAMP

from app.core.mysql_db import Base

class ModelConfig(Base):
    """
    模型配置表
    """
    __tablename__ = "model_config"
    id = Column(Integer, primary_key=True,comment="模型配置ID")
    model_name = Column(String(100),comment="模型名称")
    model_type = Column(String(50),comment="模型类型")
    provider = Column(String(50),comment="提供方")
    api_endpoint = Column(String(255),comment="API 地址")
    api_key = Column(String(255),comment="API 密钥")
    is_default = Column(Integer, default=0, comment="是否为默认模型")
    status = Column(String(50), default="active", comment="模型状态:active:活跃,inactive:不活跃")
    create_time = Column(TIMESTAMP, default=datetime.now, comment="创建时间")
    update_time = Column(TIMESTAMP, default=datetime.now, onupdate=datetime.now, comment="更新时间")
