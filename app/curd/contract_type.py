"""
@Project ：Contract_Review_backend-Py 
@File    ：contract_type.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/31 16:48 
"""
from sqlalchemy.orm import Session
from app.models import ContractType
from app.schemas.contract_type import ContractTypeSchema

async def get_contract_type(db: Session, contract_type_id: int):
    """
    根据合同类型ID获取合同类型
    """
    return db.query(ContractType).filter(ContractType.id == contract_type_id).first()

async def get_contract_type_list(db: Session):
    """
    获取所有合同类型
    """
    return db.query(ContractType).filter(ContractType.is_active == 1).all()

async def create_contract_type(db: Session, contract_type: ContractTypeSchema):
    """
    创建合同类型
    """
    db_contract_type = ContractType(
        name=contract_type.name,
        description=contract_type.description,
    )
    db.add(db_contract_type)
    db.commit()
    db.refresh(db_contract_type)
    return db_contract_type


async def update_contract_type(db: Session, contract_type_id: int, contract_type: ContractTypeSchema):
    """
    更新合同类型
    """
    db_contract_type = db.query(ContractType).filter(ContractType.id == contract_type_id).first()
    if not db_contract_type:
        return None
    if contract_type.name is not None:
        db_contract_type.name = contract_type.name
    if contract_type.description is not None:
        db_contract_type.description = contract_type.description
    db.commit()
    db.refresh(db_contract_type)
    return db_contract_type


async def inactive_contract_type(db: Session, contract_type_id: int):
    """
    停用合同类型
    """
    db_contract_type = db.query(ContractType).filter(ContractType.id == contract_type_id).first()
    if not db_contract_type:
        return None
    db_contract_type.is_active = 0
    db.commit()
    db.refresh(db_contract_type)
    return db_contract_type
