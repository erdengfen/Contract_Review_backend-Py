"""
@Project ：Contract_Review_backend-Py 
@File    ：contract_type.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/31 16:50 
"""
from datetime import datetime

from pydantic import BaseModel, Field


class ContractTypeSchema(BaseModel):
    """
    合同类型表
    """
    name: str = Field(..., description="合同类型名称")
    description: str = Field(..., description="合同类型描述")


class ContractTypeResponse(BaseModel):
    """
    合同类型响应表
    """
    id: int = Field(..., description="合同类型ID")

    name: str = Field(..., description="合同类型名称")
    description: str = Field(..., description="合同类型描述")
    class Config:
        from_attributes = True
