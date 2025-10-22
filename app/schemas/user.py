"""
@Project ：Contract_Review_backend-Py 
@File    ：user.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/22 09:57 
"""
from typing import Optional

from pydantic import BaseModel, Field


class TokenData(BaseModel):
    """
    令牌数据模型
    """
    username: str | None = None


class UserCreate(BaseModel):
    username: str
    password: str


class UserUpdate(BaseModel):
    username: str | None = None
    password: str | None = None


class UserResponse(BaseModel):
    id: int
    username: Optional[str]=Field(None,description="用户名")
    is_active: Optional[bool] = Field(True,description="是否活跃")

    class Config:
        orm_mode = True

# --------------------login----------------------


class LoginRequest(BaseModel):
    identifier: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")

class LoginResponse(BaseModel):
    access_token: Optional[str]=Field(None,description="访问令牌")
    token_type: Optional[str]=Field(None,description="令牌类型")
    refresh_token: Optional[str]=Field(None,description="刷新令牌")
