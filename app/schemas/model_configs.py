"""
@Project ：Contract_Review_backend-Py 
@File    ：model_configs.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/11/2 10:58 
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ModelConfigCreate(BaseModel):
    """
    模型配置创建模型
    """
    model_name: str
    model_type: str
    provider: str
    api_endpoint: Optional[str] = None
    api_key: Optional[str] = None
    is_default: int = 0  # 0 or 1
    status: str = "active"


class ModelConfigUpdate(BaseModel):
    """
    模型配置更新模型
    """
    model_name: Optional[str] = None
    model_type: Optional[str] = None
    provider: Optional[str] = None
    api_endpoint: Optional[str] = None
    api_key: Optional[str] = None
    is_default: Optional[int] = None
    status: Optional[str] = None


class ModelConfigResponse(ModelConfigCreate):
    """
    模型配置响应模型
    """
    id: int
    create_time: datetime
    update_time: datetime

    class Config:
        from_attributes = True