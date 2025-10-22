"""
@Project ：Contract_Review_backend-Py 
@File    ：contract.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/22 14:45 
"""


from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.config.config import settings
router = APIRouter(tags=["合同管理"])
"""
文件上传 下载相关接口
"""

@router.post("/delete_file")
async def delete_contract(file_id):
    """
    删除指定合同文件
    """
