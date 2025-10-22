"""
@Project ：Contract_Review_backend-Py 
@File    ：login.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/22 09:51 
"""
from sqlalchemy import Column, Integer, String

from app.core.mysql_db import Base


class User(Base):
    __tablename__ = "user"

    user_id = Column(Integer, primary_key=True,comment="用户ID")
    user_name = Column(String(50),comment="用户名")
    mobile = Column(String(11),comment="手机号")
    password = Column(String(255),comment="密码")
    status = Column(Integer,comment="状态")
