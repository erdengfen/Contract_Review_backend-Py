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
from typing import Optional

from sqlalchemy.orm import Session as DBSession

from app.config.config import settings
from app.core.global_init import llm_manager
from app.models.contract import ContractFile
from app.models.contract_type import ContractType
from app.models.user import User
from app.schemas.contract_file import UploadResponse
from app.utils.contract_parser import ContractParser

from urllib.parse import quote

class CRUDContractType:
    """合同类型CRUD操作"""
    @staticmethod
    def get_contract_type(db: DBSession, contract_type_name: str):
        """根据合同类型名称获取合同类型"""
        return db.query(ContractType).filter(ContractType.name == contract_type_name).first()

class CRUDContract:

    @staticmethod
    async def create_contract_file(
            db: DBSession,
            type: str,
            user_id: int,
            file_name: str,
            file_type: str,
            # contract_content: str,
            contract_content_path: str,
            save_path: str,
            party_a: str,
            party_b: str,
            amount: float,
    ) -> UploadResponse:
        """上传并保存合同文件"""

        new_file = ContractFile(
            type=type,
            user_id=user_id,
            title=file_name,
            # contract_content=contract_content,
            contract_content_path=contract_content_path,
            file_path=save_path,
            file_type=file_type,
            party_a=party_a,
            party_b=party_b,
            amount=amount,
            upload_time=datetime.now(),
            status="uploaded"
        )
        db.add(new_file)
        db.commit()
        db.refresh(new_file)

        relative_path = f"/static/{user_id}/{quote(file_name)}"
        file_url =f"{relative_path}"

        return UploadResponse(
            file_id=new_file.id,
            title=new_file.title,
            file_path=new_file.file_path,
            file_type=new_file.file_type,
            file_url=file_url,
            party_a=party_a,
            party_b=party_b,
            amount=amount,
        )
    @staticmethod
    async def set_contract_type(db: DBSession, file_id: int, contract_type_id: int, review_position: int) -> bool:
        """设置合同类型"""
        contract_type = db.query(ContractType).filter(ContractType.id == contract_type_id).first()
        if not contract_type:
            return False
        file_data = db.query(ContractFile).filter(ContractFile.id == file_id).first()
        if file_data:
            file_data.contract_type_id = contract_type.id
            file_data.review_position = review_position
            db.commit()
            db.refresh(file_data)
            return True
        else:
            return False



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