"""
@Project ：Contract_Review_backend-Py 
@File    ：user.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/22 09:57 
"""
from pydantic import BaseModel


class UserCreate(BaseModel):
    user_name: str
    mobile: str
    password: str


class UserResponse(BaseModel):
    user_id: int
    user_name: str
    mobile: str
