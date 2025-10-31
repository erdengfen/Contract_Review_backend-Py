"""
@Project ：Contract_Review_backend-Py 
@File    ：contract_type.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/31 16:48 
"""


from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.schemas.base import GenericResponse
from app.core.dependencies import get_db
from app.schemas.contract_type import ContractTypeSchema, ContractTypeResponse
from app.curd.contract_type import (
    get_contract_type,
    create_contract_type,
    update_contract_type,
    inactive_contract_type, get_contract_type_list,
)

router = APIRouter(prefix="/contract-type", tags=["Contract Type Management"])

# ------------------- 查询合同类型 -------------------
@router.get("/{contract_type_id}", response_model=GenericResponse[ContractTypeResponse],summary="查询合同类型")
async def read_contract_type(
    contract_type_id: int,
    db: Session = Depends(get_db)
):
    db_contract = await get_contract_type(db, contract_type_id)
    if not db_contract:
        raise HTTPException(status_code=404, detail="Contract type not found")
    return GenericResponse(
        code=200,
        msg="获取合同类型成功",
        data=db_contract)

@router.get("/list", response_model=GenericResponse[list[ContractTypeResponse]],summary="查询合同类型列表")
async def read_contract_type_list(
    db: Session = Depends(get_db)
):
    db_contract_list = await get_contract_type_list(db)
    if not db_contract_list:
        raise HTTPException(status_code=404, detail="Contract type list not found")
    return GenericResponse(
        code=200,
        msg="获取合同类型列表成功",
        data=db_contract_list)

# ------------------- 创建合同类型 -------------------
@router.post("/create_contract_type", response_model=GenericResponse[ContractTypeResponse],summary="创建合同类型")
async def create_new_contract_type(
    contract_type: ContractTypeSchema,
    db: Session = Depends(get_db)
):
    try:
        result = await create_contract_type(db, contract_type)
        return GenericResponse(
            code=200,
            msg="创建合同类型成功",
            data=result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create contract type: {str(e)}")


# ------------------- 更新合同类型 -------------------
@router.post("/update_contract_type", response_model=GenericResponse[ContractTypeResponse],summary="更新合同类型")
async def update_existing_contract_type(
    contract_type_id: int = Query(..., description="合同类型ID"),
    contract_type: ContractTypeSchema = None,
    db: Session = Depends(get_db)
):
    if contract_type is None:
        contract_type = ContractTypeSchema(name="", description="")  # 或抛出错误
    result = await update_contract_type(db, contract_type_id, contract_type)
    if not result:
        raise HTTPException(status_code=404, detail="Contract type not found")
    return GenericResponse(
        code=200,
        msg="更新合同类型成功",
        data=ContractTypeResponse.model_validate(result))


# ------------------- 停用合同类型 -------------------
@router.post("/inactive_contract_type", response_model=GenericResponse[ContractTypeResponse],summary="停用合同类型")
async def deactivate_contract_type(
    contract_type_id: int = Query(..., description="要停用的合同类型ID"),
    db: Session = Depends(get_db)
):
    result = await inactive_contract_type(db, contract_type_id)
    if not result:
        raise HTTPException(status_code=404, detail="Contract type not found")
    return GenericResponse(
        code=200,
        msg="停用合同类型成功",
        data=ContractTypeResponse.model_validate(result))
