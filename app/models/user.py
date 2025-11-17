"""
@Project ：Contract_Review_backend-Py 
@File    ：login.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/22 09:51 
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, TIMESTAMP, Boolean

from app.core.mysql_db import Base


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True,comment="用户ID")
    username = Column(String(64),comment="用户名")
    password = Column(String(128),comment="密码哈希")
    is_active = Column(Integer, default=1, comment="是否活跃（1: 活跃, 0: 禁用）")
    created_at = Column(TIMESTAMP, default=datetime.now, comment="创建时间")

class UserLLMConfig(Base):
    __tablename__ = "models"

    id = Column(Integer, primary_key=True,comment="模型ID")
    user_id = Column(Integer, comment="用户")
    api_key = Column(String(128),comment="APIkey")
    model_name = Column(String(128),comment="模型名称")
    model_provider = Column(String(128),comment="模型供应商")
    base_url = Column(String(128),comment="模型url")
    is_active = Column(Boolean, default=False, comment="是否为当前使用模型")
    # 新增字段：员工ID、部门
    employee_id = Column(String(64),comment="员工ID")
    department = Column(String(64),comment="部门")
    role=Column(Integer,default=1,comment="角色:1-普通用户,2-教师")
