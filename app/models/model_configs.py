"""
@Project ：Contract_Review_backend-Py 
@File    ：model_configs.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/11/2 10:55 
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, TIMESTAMP, Float, func

from app.core.mysql_db import Base

class ModelConfig(Base):
    __tablename__ = "model_config"

    id = Column(Integer, primary_key=True, comment="模型配置ID")
    model_name = Column(String(100), comment="模型名称")
    model_type = Column(String(50), comment="模型类型")
    provider = Column(String(50), comment="提供方")
    api_endpoint = Column(String(255), comment="API 地址")
    api_key = Column(String(255), comment="API 密钥")
    temperature = Column(Float, default=0.7, comment="温度参数")
    top_p = Column(Float, default=0.95, comment="Top-p 参数")
    presence_penalty = Column(Float, default=0.0, comment="存在惩罚参数")
    frequency_penalty = Column(Float, default=0.0, comment="频率惩罚参数")
    max_tokens = Column(Integer, default=2048, comment="最大令牌数")
    is_default = Column(Integer, default=0, comment="是否为默认模型 (0/1)")
    status = Column(String(50), default="active", comment="模型状态: active/inactive")
    create_time = Column(TIMESTAMP, default=datetime.now, comment="创建时间")
    update_time = Column(TIMESTAMP, default=datetime.now, onupdate=datetime.now, comment="更新时间")
