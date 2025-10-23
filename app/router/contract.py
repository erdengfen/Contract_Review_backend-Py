"""
@Project ：Contract_Review_backend-Py 
@File    ：contract.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/22 14:45 
"""
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session
from app.core.dependencies import get_db
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from app.config.config import settings
from app.middlewares.auth import optional_get_current_user
from app.models import ContractFile
from  app.schemas.base import GenericResponse
from app.schemas.contract_file import UploadResponse


router = APIRouter(tags=["合同管理"])
"""
文件上传 下载相关接口
"""


@router.post("/upload", response_model=GenericResponse[UploadResponse], summary="上传合同文件")
async def upload_file(
    current_user=Depends(optional_get_current_user),
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
):
    """上传合同文件"""
    if not current_user:
        return GenericResponse(code=401, msg="用户未登录")

    if not file.filename:
        return GenericResponse(code=400, msg="文件名不能为空")

    try:
        file_type = file.filename.split(".")[-1]
        save_path = os.path.join(settings.UPLOAD_DIR, file.filename)

        with open(save_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        new_file = ContractFile(
            user_id=current_user.id,
            title=file.filename,
            file_path=save_path,
            file_type=file_type,
            upload_time=datetime.now(),
            status="uploaded"
        )
        db.add(new_file)
        db.commit()
        db.refresh(new_file)

        return GenericResponse(
            code=200,
            msg="上传成功",
            data=UploadResponse(
                file_id=new_file.id,
                title=new_file.title,
                file_path=new_file.file_path,
                file_type=new_file.file_type
            )
        )
    except Exception as e:
        db.rollback()
        return GenericResponse(code=500, msg=f"文件上传失败: {str(e)}")


@router.get("/download/{file_id}", summary="下载文件")
async def download_file(file_id: int, db: Session = Depends(get_db)):
    """下载文件"""
    file_record = db.query(ContractFile).filter(ContractFile.id == file_id).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="文件不存在")

    file_path = file_record.file_path
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件已丢失")

    return FileResponse(
        path=file_path,
        filename=os.path.basename(file_path),
        media_type="application/octet-stream"
    )


