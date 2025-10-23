"""
@Project ：Contract_Review_backend-Py 
@File    ：contract.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/22 15:18 
"""
from openai import BaseModel
from pydantic import Field




class UploadResponse(BaseModel):
    file_id: int = Field(..., description="合同文件ID")
    title: str = Field(..., description="合同标题")
    file_path: str = Field(..., description="合同文件路径")
    file_type: str = Field(..., description="合同文件类型")
    file_url: str = Field(..., description="文件访问URL")

    class Config:
        orm_mode = True
