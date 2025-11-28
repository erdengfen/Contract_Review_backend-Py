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
    file_id: Optional[int] = Field(..., description="合同文件ID")
    title: Optional[str] = Field(..., description="合同标题")
    file_path: Optional[str] = Field(..., description="合同文件路径")
    file_type: Optional[str] = Field(..., description="合同文件类型")
    file_url: Optional[str] = Field(..., description="文件访问URL")
    party_a: Optional[str] = Field(..., description="甲方名称")
    party_b: Optional[str] = Field(..., description="乙方名称")
    amount: Optional[float] = Field(..., description="合同金额")

class Config:
    from_attributes = True

class TransformContractRequest(BaseModel):
    html_content: str = Field(..., description="合同文件HTML内容")
    title: str = Field(..., description="合同标题")
