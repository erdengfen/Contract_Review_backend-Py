"""
@Project ：Contract_Review_backend-Py 
@File    ：contract.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/22 15:18 
"""
from typing import Optional

from openai import BaseModel
from pydantic import Field




class UploadResponse(BaseModel):
    file_id: int = Field(..., description="合同文件ID")
    title: str = Field(..., description="合同标题")
    file_path: str = Field(..., description="合同文件路径")
    file_type: str = Field(..., description="合同文件类型")
    file_url: str = Field(..., description="文件访问URL")
    party_a: Optional[str] = Field(None, description="甲方信息")
    party_b: Optional[str] = Field(None, description="乙方信息")
    contract_value: Optional[str] = Field(None, description="合同金额")

    class Config:
        orm_mode = True
