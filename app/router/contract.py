"""
@Project ：Contract_Review_backend-Py 
@File    ：contract.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/22 14:45 
"""
import os

from sqlalchemy.orm import Session
from app.core.dependencies import get_db
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends

from app.curd.contract_file import CRUDContract
from app.middlewares.auth import optional_get_current_user

from  app.schemas.base import GenericResponse
from app.schemas.contract_file import UploadResponse
from fastapi.responses import FileResponse

router = APIRouter(tags=["合同管理"])
"""
文件上传 下载相关接口
"""


@router.post("/upload", response_model=GenericResponse[UploadResponse], summary="上传合同文件")
async def upload_contract_file(
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
        upload_result =await CRUDContract.create_contract_file(db=db, user_id=current_user.id, file=file)
        return GenericResponse(code=200, msg="上传成功", data=upload_result)
    except Exception as e:
        db.rollback()
        return GenericResponse(code=500, msg=f"文件上传失败: {str(e)}")


@router.get("/download/{file_id}", summary="下载文件")
async def download_contract_file(file_id: int, db: Session = Depends(get_db)):
    """下载合同文件"""
    file_record =await CRUDContract.get_contract_file(db=db, file_id=file_id)
    if not file_record:
        raise HTTPException(status_code=404, detail="文件不存在")

    if not os.path.exists(file_record.file_path):
        raise HTTPException(status_code=404, detail="文件已丢失")

    return FileResponse(
        path=file_record.file_path,
        filename=os.path.basename(file_record.file_path),
        media_type="application/octet-stream"
    )


@router.delete("/{file_id}", response_model=GenericResponse, summary="删除合同文件")
async def delete_contract_file(file_id: int, db: Session = Depends(get_db)):
    """删除合同文件"""
    success =await CRUDContract.delete_contract_file(db=db, file_id=file_id)
    if not success:
        return GenericResponse(code=404, msg="文件不存在或删除失败")
    return GenericResponse(code=200, msg="文件删除成功")


