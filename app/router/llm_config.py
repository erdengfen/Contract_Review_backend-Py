from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.dependencies import get_db
from app.models.user import UserLLMConfig
from app.schemas.llm_config import LLMConfigResponse, LLMConfigCreate
from app.core.global_init import llm_manager

router = APIRouter(tags=["LLM配置"])

"""
llm管理相关接口
"""

@router.get("/configs/{user_id}", response_model=List[LLMConfigResponse])
async def get_user_llm_configs(user_id: int, db: Session = Depends(get_db)):
    """获取指定用户的所有 LLM 模型配置"""
    configs = db.query(UserLLMConfig).filter_by(user_id=user_id).all()
    if not configs:
        raise HTTPException(status_code=404, detail="该用户未配置任何模型")
    return [
        {
            "model_name": c.model_name,
            "model_provider": c.model_provider,
            "base_url": c.base_url,
            "api_key": c.api_key,
        }
        for c in configs
    ]


@router.post("/config/{user_id}")
async def set_user_llm_config(
    user_id: int,
    config: LLMConfigCreate,
    db: Session = Depends(get_db),
):
    """新增或更新用户的某个模型配置"""
    await llm_manager.set_user_llm_config(
        db_session=db,
        user_id=user_id,
        api_key=config.api_key,
        model_name=config.model_name,
        model_provider=config.model_provider,
        base_url=config.base_url,
    )
    return {"message": f"模型 {config.model_name} 配置已保存"}


@router.delete("/config/{user_id}/{model_name}")
async def delete_user_llm_config(user_id: int, model_name: str, db: Session = Depends(get_db)):
    """删除用户的某个模型配置"""
    model = db.query(UserLLMConfig).filter_by(user_id=user_id, model_name=model_name).first()
    if not model:
        raise HTTPException(status_code=404, detail="未找到该模型配置")

    db.delete(model)
    db.commit()
    await llm_manager.clear_user_llm_cache(user_id, model_name)
    return {"message": f"模型 {model_name} 已删除"}


@router.put("/active/{user_id}")
async def set_active_model(user_id: int, model_name: str, db: Session = Depends(get_db)):
    """切换当前使用的模型"""
    try:
        await llm_manager.set_active_model(user_id=user_id, model_name=model_name, db_session=db)
        return {"message": f"当前已切换为模型 {model_name}"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
