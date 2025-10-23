"""
@Project ：Contract_Review_backend-Py 
@File    ：contract_file.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/22 15:41 
"""
import os
import shutil
from datetime import datetime

from sqlalchemy.orm import Session as DBSession

from app.config.config import settings
from app.models.contract import ContractFile
from app.models.user import User
from app.schemas.contract_file import UploadResponse


from urllib.parse import quote

class CRUDContract:

    @staticmethod
    async def create_contract_file(db: DBSession, user_id: int, file) -> UploadResponse:
        """上传并保存合同文件"""
        file_type = file.filename.split(".")[-1]
        save_dir = os.path.join(settings.UPLOAD_DIR, str(user_id))
        os.makedirs(save_dir, exist_ok=True)

        save_path = os.path.join(save_dir, file.filename)
        with open(save_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        new_file = ContractFile(
            user_id=user_id,
            title=file.filename,
            file_path=save_path,
            file_type=file_type,
            upload_time=datetime.now(),
            status="uploaded"
        )
        db.add(new_file)
        db.commit()
        db.refresh(new_file)

        # 构造文件访问 URL（静态映射路径）
        # 注意 URL 中中文或空格文件名要编码
        relative_path = f"/static/{user_id}/{quote(file.filename)}"
        file_url =f"{relative_path}"

        return UploadResponse(
            file_id=new_file.id,
            title=new_file.title,
            file_path=new_file.file_path,
            file_type=new_file.file_type,
            file_url=file_url
        )


    @staticmethod
    async def get_contract_file(db: DBSession, file_id: int) -> ContractFile:
        """根据文件ID查询合同文件"""
        return db.query(ContractFile).filter(ContractFile.id == file_id).first()


    @staticmethod
    async def delete_contract_file(db: DBSession, file_id: int) -> bool:
        """

        :param file_id:
        :return:
        """
        file_data= db.query(ContractFile).filter(ContractFile.id == file_id).first()
        if file_data:

            file_data.status = "deleted"
            db.commit()
            db.refresh(file_data)
            return True
        else:
            return False