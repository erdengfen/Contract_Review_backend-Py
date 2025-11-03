"""
@Project ：Contract_Review_backend-Py 
@File    ：model_configs.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/11/2 10:56 
"""
from sqlalchemy import and_
from sqlalchemy.orm import Session
from typing import Optional, List, Type
from app.models.model_configs import ModelConfig
from app.schemas.model_configs import ModelConfigCreate, ModelConfigUpdate



async def get_model_configs(db: Session, skip: int = 0, limit: int = 100) -> list[Type[ModelConfig]]:
    """
    获取所有模型配置
    :param db: 数据库会话
    :param skip: 偏移量
    :param limit: 限制数量
    :return: 模型配置列表
    """
    return db.query(ModelConfig).offset(skip).limit(limit).all()



async def get_model_config_by_id(db: Session, model_id: int) -> Optional[ModelConfig]:
    """
    根据 ID 获取单个模型配置
    :param db: 数据库会话
    :param model_id: 模型配置 ID
    :return: 模型配置对象（如果存在）
    """
    return db.query(ModelConfig).filter(ModelConfig.id == model_id).first()



async def get_default_model_by_type(db: Session, model_type: str) -> Optional[ModelConfig]:
    """
    根据模型类型获取默认模型（is_default=1 且 status='active'）
    :param db: 数据库会话
    :param model_type: 模型类型
    :return: 默认模型配置对象（如果存在）
    """
    return db.query(ModelConfig).filter(
        and_(
            ModelConfig.model_type == model_type,
            ModelConfig.is_default == 1,
            ModelConfig.status == "active"
        )
    ).first()



async def create_model_config(db: Session, config: ModelConfigCreate) -> ModelConfig:
    """
    创建新的模型配置
    :param db: 数据库会话
    :param config: 模型配置创建模型
    :return: 创建的模型配置对象
    """
    # 如果新模型被设为默认，则需先取消同类型的其他默认模型
    if config.is_default == 1:
        db.query(ModelConfig).filter(
            ModelConfig.model_type == config.model_type
        ).update({"is_default": 0})

    db_config = ModelConfig(**config.model_dump())
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    return db_config



async def update_model_config(db: Session, model_id: int, config_update: ModelConfigUpdate) -> Optional[
    ModelConfig]:
    """
    更新模型配置
    :param db: 数据库会话
    :param model_id: 模型配置 ID
    :param config_update: 模型配置更新模型
    :return: 更新后的模型配置对象（如果存在）
    """
    db_config = get_model_config_by_id(db, model_id)
    if not db_config:
        return None

    update_data = config_update.model_dump(exclude_unset=True)

    # 如果 is_default 被设为 1，则清除同类型的其他默认项
    if update_data.get("is_default") == 1:
        db.query(ModelConfig).filter(
            ModelConfig.model_type == db_config.model_type
        ).update({"is_default": 0})

    for key, value in update_data.items():
        setattr(db_config, key, value)

    db.commit()
    db.refresh(db_config)
    return db_config



async def delete_model_config(db: Session, model_id: int) -> bool:
    """
    删除模型配置（硬删除）
    :param db: 数据库会话
    :param model_id: 模型配置 ID
    :return: 是否删除成功
    """
    db_config = get_model_config_by_id(db, model_id)
    if db_config:
        db.delete(db_config)
        db.commit()
        return True
    return False