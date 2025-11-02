"""
@Project ：Contract_Review_backend-Py 
@File    ：model_configs.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/11/2 10:56 
"""
from datetime import datetime

from sqlalchemy import and_
from sqlalchemy.orm import Session
from typing import Optional, List, Type

from app.models import ModelConfig
from app.models.model_configs import ModelConfig

from app.schemas.model_configs import ModelConfigCreate, ModelConfigUpdate, ModelConfigResponse


async def get_model_configs(db: Session, page: int = 0, size: int = 100) -> List[ModelConfig]:
    skip = (page - 1) * size
    return db.query(ModelConfig).offset(skip).limit(size).all()


async def get_model_config_by_id(db: Session, model_id: int) -> Optional[ModelConfig]:
    return db.query(ModelConfig).filter(ModelConfig.id == model_id).first()


async def get_default_model_by_type(db: Session, model_type: str) -> Optional[ModelConfig]:
    return db.query(ModelConfig).filter(
        and_(
            ModelConfig.model_type == model_type,
            ModelConfig.is_default == 1,
            ModelConfig.status == "active"
        )
    ).first()


async def create_model_config(db: Session, config: ModelConfigCreate) -> ModelConfig:
    if config.is_default == 1:
        db.query(ModelConfig).filter(ModelConfig.model_type == config.model_type).update({"is_default": 0})
    create_time = datetime.now()
    db_config = ModelConfig(**config.model_dump(), create_time=create_time, update_time=create_time)
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    return db_config


async def update_model_config(db: Session, model_id: int, config_update: ModelConfigUpdate) -> Optional[ModelConfig]:
    db_config = await get_model_config_by_id(db, model_id)
    if not db_config:
        return None
    update_data = config_update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        if hasattr(db_config, key):
            setattr(db_config, key, value)
    db_config.update_time = datetime.now()

    db.commit()
    db.refresh(db_config)
    return db_config


async def delete_model_config(db: Session, model_id: int) -> bool:
    db_config = await get_model_config_by_id(db, model_id)
    if db_config:
        db.delete(db_config)
        db.commit()
        return True
    return False