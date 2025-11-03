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

@router.post("/models/", response_model=GenericResponse[ModelConfigResponse],summary="创建模型配置")
async def create_model(config: ModelConfigCreate, db: Session = Depends(get_db)):
    """
    创建模型配置
    :param config: 模型配置数据
    :param db: 数据库会话
    :return: 创建的模型配置对象
    """
    try:
        model = await create_model_config(db=db, config=config)
        return GenericResponse(
            code=200,
            msg="模型配置创建成功",
            data=model
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/models/{model_id}", response_model=GenericResponse[ModelConfigResponse],summary="更新模型配置")
async def update_model(model_id: int, config: ModelConfigUpdate, db: Session = Depends(get_db)):
    """
    更新模型配置
    :param model_id: 模型配置 ID
    :param config: 更新的模型配置数据
    :param db: 数据库会话
    :return: 更新后的模型配置对象
    """
    try:
        db_model = await update_model_config(db=db, model_id=model_id, config_update=config)
        if not db_model:
            raise HTTPException(status_code=404, detail="Model not found")
        return GenericResponse(
            code=200,
            msg="模型配置更新成功",
            data=db_model
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        raise HTTPException(status_code=404, detail="Model not found")
    return db_model

@router.get("/models/default/{model_type}", response_model=ModelConfigResponse,summary="获取默认模型配置")
async def get_default_model(model_type: str, db: Session = Depends(get_db)):
    """
    获取默认模型配置
    :param model_type: 模型类型
    :param db: 数据库会话
    :return: 默认模型配置对象
    """
    model = await get_default_model_by_type(db, model_type)
    if not model:
        raise HTTPException(status_code=404, detail="No default model found for this type")
    return GenericResponse(
        code=200,
        msg="默认模型配置获取成功",
        data=model
    )




@router.get("/models/", response_model=GenericResponse[List[ModelConfigResponse]], summary="获取所有模型配置")
async def read_all_models(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    获取所有模型配置
    :param skip: 偏移量
    :param limit: 限制数量
    :param db: 数据库会话
    :return: 模型配置列表
    """
    models =await get_model_configs(db, skip=skip, limit=limit)
    return GenericResponse(
        code=200,
        msg="所有模型配置获取成功",
        data=models
    )



@router.get("/models/{model_id}", response_model=GenericResponse[ModelConfigResponse], summary="根据ID获取模型配置")
async def read_model_by_id(model_id: int, db: Session = Depends(get_db)):
    """
    根据 ID 获取单个模型配置
    :param model_id: 模型配置 ID
    :param db: 数据库会话
    :return: 模型配置对象（如果存在）
    """
    model = await get_model_config_by_id(db, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return GenericResponse(
        code=200,
        msg="模型配置获取成功",
        data=model
    )



@router.delete("/models/{model_id}", response_model=GenericResponse[dict], summary="删除模型配置")
async def delete_model(model_id: int, db: Session = Depends(get_db)):
    """
    删除模型配置
    :param model_id: 模型配置 ID
    :param db: 数据库会话
    :return: 删除成功消息
    """
    success = await delete_model_config(db, model_id)
    if not success:
        raise HTTPException(status_code=404, detail="Model not found or already deleted")
    return GenericResponse(
        code=200,
        msg="模型配置删除成功",
        data={}
    )
