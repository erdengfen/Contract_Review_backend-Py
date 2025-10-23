"""
@Project ：Contract_Review_backend-Py 
@File    ：contract.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/22 15:18 
"""
from openai import BaseModel
from typing import Optional
from pydantic import Field




class UploadResponse(BaseModel):
    file_id: int
    title: str
    file_path: str
    file_type: str