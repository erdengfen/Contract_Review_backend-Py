"""
@Project ：Contract_Review_backend-Py 
@File    ：prompt_manage.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/30 16:26 
"""
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session as DBSession
from app.utils.logs_utils import log_module
from app.models.prompt_manage import (
    SystemPrompt,
    BasePrompt,
    PromptOverrides
)

from app.schemas.prompt_manage import SystemPromptSchema, PromptOverridesSchema, \
    UpdateSystemPromptSchema, UpdateBasePromptSchema, UpdatePromptOverridesSchema


# --------------基础prompt------------------------------------------------
async  def create_system_prompt(db: DBSession, prompt: SystemPromptSchema):
    """
    创建基础 Prompt
    """
    db_prompt = SystemPrompt(
        contract_type_id=prompt.contract_type_id,
        prompt_name=prompt.prompt_name,
        prompt_text=prompt.prompt_content,
    )
    db.add(db_prompt)
    db.commit()
    db.refresh(db_prompt)
    return db_prompt

async  def update_system_prompt(db: DBSession, base_prompt_id: int, prompt: UpdateSystemPromptSchema):
    """
    更新基础 Prompt
    """
    db_prompt = db.query(SystemPrompt).filter(SystemPrompt.id == base_prompt_id).first()
    if not db_prompt:
        return None
    if prompt.contract_type_id is not None:
        db_prompt.contract_type_id = prompt.contract_type_id
    if prompt.prompt_name is not None:
        db_prompt.prompt_name = prompt.prompt_name
    if prompt.prompt_content is not None:
        db_prompt.prompt_text = prompt.prompt_content
    db.commit()
    db.refresh(db_prompt)
    return db_prompt


async  def  get_system_prompt_id(db: DBSession, base_prompt_id: int):
    """
    根据基础PromptID获取基础Prompt
    """
    db_prompt = db.query(SystemPrompt).filter(SystemPrompt.id == base_prompt_id).first()
    if not db_prompt:
        return None
    return db_prompt.id

async  def get_system_prompt_contract_type_id(db: DBSession, contract_type_id: int):
    """
    根据合同类型ID获取基础Prompt
    """
    db_prompt = db.query(SystemPrompt).filter(SystemPrompt.contract_type_id == contract_type_id).first()
    if not db_prompt:
        return None
    return db_prompt.contract_type_id

async  def get_system_prompt_list(db: DBSession):
    """
    获取所有基础Prompt列表
    """
    db_prompt_list = db.query(SystemPrompt).all()
    if not db_prompt_list:
        return None
    return db_prompt_list

# --------------------机构prompt------------------------------------------------

async def get_base_prompt(db: DBSession,contract_type_id: int,organization_id: int):
    """
    根据合同类型ID获取机构Prompt
    """
    # 先获取机构prompt 为空获取基础prompt 并添加到机构prompt表
    db_prompt = db.query(BasePrompt).filter(BasePrompt.contract_type_id == contract_type_id,
                                           BasePrompt.organization_id == organization_id).first()
    if not db_prompt:
        system_prompt = db.query(SystemPrompt).filter(SystemPrompt.contract_type_id == contract_type_id).first()
        if not system_prompt:
            return None
        # 添加到机构prompt表
        prompt = BasePrompt(
            contract_type_id=contract_type_id,
            organization_id=organization_id,
            system_prompt_id=system_prompt.id,
            prompt_name=system_prompt.prompt_name,
            prompt_text=system_prompt.prompt_text,
            is_override=0,
        )
        db.add(prompt)
        db.commit()
        db.refresh(prompt)
        db_prompt=prompt
    return db_prompt



async  def update_base_prompt(db: DBSession, prompt: UpdateBasePromptSchema):
    """
    更新机构 Prompt 内容
    """
    db_prompt = db.query(BasePrompt).filter( BasePrompt.id == prompt.base_prompt_id,
                                              BasePrompt.organization_id == prompt.organization_id).first()
    if not db_prompt:
        return None
    # if prompt.contract_type_id is not None:
    #     db_prompt.contract_type_id = prompt.contract_type_id
    if prompt.prompt_name is not None:
        db_prompt.prompt_name = prompt.prompt_name
    if prompt.prompt_text is not None:
        db_prompt.prompt_text = prompt.prompt_text
    db.commit()
    db.refresh(db_prompt)
    return db_prompt


async def get_base_prompt_id(db: DBSession,base_prompt_id: int,organization_id: int):
    """
    根据基础PromptID获取机构PromptID
    """
    db_prompt = db.query(BasePrompt).filter(BasePrompt.id == base_prompt_id,
                                           BasePrompt.organization_id == organization_id).first()
    if not db_prompt:
        return None
    return db_prompt




async def restore_base_prompt(db: DBSession, base_prompt_id: int, organization_id: int):
    """
    恢复机构 Prompt 到默认状态
    """
    db_prompt = db.query(BasePrompt).filter(BasePrompt.id == base_prompt_id,
                                           BasePrompt.organization_id == organization_id).first()

    if not db_prompt:
        return None
    system_prompt = db.query(SystemPrompt).filter(SystemPrompt.id == db_prompt.system_prompt_id).first()
    if not system_prompt:
        return None
    db_prompt.is_override = 0
    db_prompt.prompt_name = system_prompt.prompt_name
    db_prompt.prompt_text = system_prompt.prompt_text
    db_prompt.contract_type_id = system_prompt.contract_type_id
    db.commit()
    db.refresh(db_prompt)
    # 查询个性化prompt 是否存在 存在也需要删除
    override_prompt = db.query(PromptOverrides).filter(
        PromptOverrides.system_base_prompt_id == db_prompt.id,).all()
    if override_prompt:
        for prompt in override_prompt:
            db.delete(prompt)
        db.commit()
    return db_prompt


# --------------------个性化prompt------------------------------------------------

async  def create_prompt_override(db: DBSession, prompt: PromptOverridesSchema):
    """
    创建个性化 Prompt
    """
    db_prompt = db.query(BasePrompt).filter(BasePrompt.id == prompt.base_prompt_id).first()
    if not db_prompt:
        return None

    overrides_prompt = PromptOverrides(
        base_prompt_id=db_prompt.id,
        organization_id=db_prompt.organization_id,
        override_name=prompt.override_name,
        override_text=prompt.override_text,
    )
    db.add(overrides_prompt)
    db.commit()
    db.refresh(overrides_prompt)
    return overrides_prompt


async def update_prompt_override(db: DBSession, prompt: UpdatePromptOverridesSchema):
    """
    更新个性化 Prompt
    """
    override_prompt = db.query(PromptOverrides).filter(
        PromptOverrides.id == prompt.id).first()
    if not override_prompt:
        return None
    if prompt.override_name is not None:
        override_prompt.override_name = prompt.override_name
    if prompt.override_text is not None:
        override_prompt.override_text = prompt.override_text
    db.commit()
    db.refresh(override_prompt)
    return override_prompt


async def delete_prompt_override(db: DBSession, prompt_id: int):
    """
    删除个性化 Prompt
    """
    override_prompt = db.query(PromptOverrides).filter(
        PromptOverrides.id == prompt_id).first()
    if not override_prompt:
        return None
    db.delete(override_prompt)
    db.commit()
    return override_prompt


