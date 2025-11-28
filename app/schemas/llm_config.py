from pydantic import BaseModel
from typing import Optional


class LLMConfigCreate(BaseModel):
    """用户模型信息"""
    api_key: str
    model_name: str
    model_provider: Optional[str] = None
    base_url: Optional[str] = None


class LLMConfigResponse(BaseModel):
    """更新模型配置"""
    model_name: str
    model_provider: Optional[str]
    base_url: Optional[str]
    api_key: Optional[str]

    class Config:
        orm_mode = True
