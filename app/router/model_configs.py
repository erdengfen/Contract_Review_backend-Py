"""
@Project ：Contract_Review_backend-Py 
@File    ：model_configs.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/11/2 11:04 
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.base import GenericResponse
from app.core.dependencies import get_db
from app.curd.model_configs import create_model_config, update_model_config, get_default_model_by_type, \
    get_model_config_by_id, delete_model_config, get_model_configs
from app.schemas.model_configs import ModelConfigCreate, ModelConfigResponse, ModelConfigUpdate

router = APIRouter(tags=["模型配置"])
@router.post("/create_model/", response_model=GenericResponse[ModelConfigResponse], summary="创建模型配置")
async def create_model(config: ModelConfigCreate, db: Session = Depends(get_db)):
    try:
        model = await create_model_config(db=db, config=config)
        return GenericResponse(code=200, msg="模型配置创建成功", data=model)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update_model/{model_id}", response_model=GenericResponse[ModelConfigResponse], summary="更新模型配置")
async def update_model(model_id: int, config: ModelConfigUpdate, db: Session = Depends(get_db)):
    db_model = await update_model_config(db=db, model_id=model_id, config_update=config)
    if not db_model:
        raise HTTPException(status_code=404, detail="Model not found")
    return GenericResponse(code=200, msg="模型配置更新成功", data=db_model)


@router.get("/get_default_model/{model_type}", response_model=GenericResponse[ModelConfigResponse], summary="获取默认模型配置")
async def get_default_model(model_type: str, db: Session = Depends(get_db)):
    model = await get_default_model_by_type(db, model_type)
    if not model:
        raise HTTPException(status_code=404, detail="No default model found for this type")
    return GenericResponse(code=200, msg="默认模型配置获取成功", data=model)


@router.get("/get_all_models/", response_model=GenericResponse[List[ModelConfigResponse]], summary="获取所有模型配置")
async def read_all_models(page: int = 0, size: int = 100, db: Session = Depends(get_db)):
    models = await get_model_configs(db, page=page, size=size)
    return GenericResponse(code=200, msg="所有模型配置获取成功", data=models)


@router.get("/get_model_by_id/{model_id}", response_model=GenericResponse[ModelConfigResponse], summary="根据ID获取模型配置")
async def read_model_by_id(model_id: int, db: Session = Depends(get_db)):
    model = await get_model_config_by_id(db, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return GenericResponse(code=200, msg="模型配置获取成功", data=model)


@router.post("/delete_model/{model_id}", response_model=GenericResponse[dict], summary="删除模型配置")
async def delete_model(model_id: int, db: Session = Depends(get_db)):
    success = await delete_model_config(db, model_id)
    if not success:
        raise HTTPException(status_code=404, detail="Model not found or already deleted")
    return GenericResponse(code=200, msg="模型配置删除成功", data={})
