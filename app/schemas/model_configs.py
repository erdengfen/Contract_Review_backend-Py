from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class ModelConfigSchema(BaseModel):
    model_name: str = Field(..., description="模型名称")
    model_type: str = Field(..., description="模型类型")
    provider: str = Field(..., description="模型提供方")
    api_endpoint: str = Field(..., description="API 地址")
    api_key: str = Field(..., description="API 密钥")
    temperature: float = Field(..., description="温度参数")
    top_p: float = Field(..., description="Top-p 参数")
    presence_penalty: float = Field(..., description="存在惩罚参数")
    frequency_penalty: float = Field(..., description="频率惩罚参数")
    max_tokens: int = Field(..., description="最大令牌数")
    is_default: int = Field(..., description="是否为默认模型")
    status: str = Field(..., description="模型状态: active:活跃, inactive:不活跃")
    create_time: datetime = Field(..., description="创建时间")
    update_time: datetime = Field(..., description="更新时间")

class ModelConfigCreate(BaseModel):
    model_name: Optional[str] = Field(None, description="模型名称")
    model_type: Optional[str] = Field(None, description="模型类型")
    provider: Optional[str] = Field(None, description="模型提供方")
    api_endpoint: Optional[str] = Field(None, description="API 地址")
    api_key: Optional[str] = Field(None, description="API 密钥")
    temperature: Optional[float] = Field(0.7, description="温度参数")
    top_p: Optional[float] = Field(0.95, description="Top-p 参数")
    presence_penalty: Optional[float] = Field(0.0, description="存在惩罚参数")
    frequency_penalty: Optional[float] = Field(0.0, description="频率惩罚参数")
    max_tokens: Optional[int] = Field(2048, description="最大令牌数")
    is_default: Optional[int] = Field(0, description="是否为默认模型")
    status: Optional[str] = Field("active", description="模型状态: active:活跃, inactive:不活跃")

    class Config:
        from_attributes = True  # 替代旧版 orm_mode=True


class ModelConfigUpdate(BaseModel):
    model_name: Optional[str] = Field(None, description="模型名称")
    model_type: Optional[str] = Field(None, description="模型类型")
    provider: Optional[str] = Field(None, description="模型提供方")
    api_endpoint: Optional[str] = Field(None, description="API 地址")
    api_key: Optional[str] = Field(None, description="API 密钥")
    temperature: Optional[float] = Field(None, description="温度参数")
    top_p: Optional[float] = Field(None, description="Top-p 参数")
    presence_penalty: Optional[float] = Field(None, description="存在惩罚参数")
    frequency_penalty: Optional[float] = Field(None, description="频率惩罚参数")
    max_tokens: Optional[int] = Field(None, description="最大令牌数")
    is_default: Optional[int] = Field(None, description="是否为默认模型")
    status: Optional[str] = Field(None, description="模型状态: active:活跃, inactive:不活跃")



class ModelConfigResponse(ModelConfigCreate):
    id: int
    create_time: datetime
    update_time: datetime

    class Config:
        from_attributes = True