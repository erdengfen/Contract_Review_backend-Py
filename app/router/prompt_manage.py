"""
@Project ：Contract_Review_backend-Py 
@File    ：prompt_manage.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/31 16:23 
"""

from app.core.dependencies import get_db
from sqlalchemy.orm import Session as DBSession, Session
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from app.schemas.base import GenericResponse
from app.schemas.prompt_manage import (
    SystemPromptSchema,
    UpdateSystemPromptSchema,
    UpdateBasePromptSchema,
    PromptOverridesSchema,
    UpdatePromptOverridesSchema, SystemPromptResponse, BasePromptResponse, PromptOverrideResponse
)
from app.curd.prompt_manage import (
    create_system_prompt,
    update_system_prompt,
    get_system_prompt_list,
    get_system_prompt_id,
    get_system_prompt_contract_type_id,
    get_base_prompt,
    update_base_prompt,
    restore_base_prompt,
    create_prompt_override,
    update_prompt_override,
    delete_prompt_override,
    get_base_prompt_id
)

router = APIRouter(tags=["Prompt管理"])


@router.post("/create_system", response_model=GenericResponse[SystemPromptResponse],summary="创建系统Prompt")
async def create_system_prompt_api(prompt: SystemPromptSchema, db: Session = Depends(get_db)):
    result = await create_system_prompt(db, prompt)
    if not result:
        raise HTTPException(status_code=400, detail="Failed to create system prompt")
    return GenericResponse(
        code=200,
        data=result,
        msg="创建系统Prompt成功"
    )

@router.post("/get_system_prompt_id", response_model=GenericResponse[dict],summary="根据Prompt ID获取系统Prompt")
async def get_system_prompt_id_api(
    contract_type_id: int = Query(..., description="合同类型 ID"),
    db: Session = Depends(get_db)
):
    result = await get_system_prompt_id(db, contract_type_id)
    if not result:
        raise HTTPException(status_code=404, detail="System prompt not found")
    return GenericResponse(
        code=200,
        data=result,
        msg="获取系统Prompt ID成功"
    )

@router.post("/system_update", response_model=GenericResponse[SystemPromptResponse],summary="更新系统Prompt")
async def update_system_prompt_api(
    base_prompt_id: int = Query(..., description="基础 Prompt ID"),
    prompt: UpdateSystemPromptSchema = None,
    db: Session = Depends(get_db)
):
    if prompt is None:
        prompt = UpdateSystemPromptSchema()
    result = await update_system_prompt(db, base_prompt_id, prompt)
    if not result:
        raise HTTPException(status_code=404, detail="System prompt not found")
    return GenericResponse(
        code=200,
        data=result,
        msg="更新系统Prompt成功"
    )


@router.get("/system_list", response_model=GenericResponse[list[SystemPromptResponse]],summary="获取系统Prompt列表")
async def list_system_prompts(db: Session = Depends(get_db)):
    result = await get_system_prompt_list(db)
    if not result:
        return GenericResponse(
            code=200,
            data=[],
            msg="获取系统Prompt列表成功"
        )
    return GenericResponse(
        code=200,
        data=result,
        msg="获取系统Prompt列表成功"
    )


# ==================== 机构 Prompt (BasePrompt) ====================

@router.get("/org", response_model=GenericResponse[BasePromptResponse],summary="获取机构Prompt")
async def get_org_prompt(
    contract_type_id: int = Query(..., description="合同类型 ID"),
    organization_id: int = Query(..., description="机构 ID"),
    db: Session = Depends(get_db)
):
    result = await get_base_prompt(db, contract_type_id, organization_id)
    if not result:
        raise HTTPException(status_code=404, detail="Base prompt not found and no system fallback")
    return GenericResponse(
        code=200,
        data=result,
        msg="获取机构Prompt成功"
    )


@router.post("/org_update", response_model=GenericResponse[BasePromptResponse],summary="更新机构Prompt")
async def update_org_prompt(
    prompt: UpdateBasePromptSchema,
    db: Session = Depends(get_db)
):
    result = await update_base_prompt(db, prompt)
    if not result:
        raise HTTPException(status_code=404, detail="Org prompt not found or org mismatch")
    return GenericResponse(
        code=200,
        data=result,
        msg="更新机构Prompt成功"
    )


@router.post("/org_restore", response_model=GenericResponse[BasePromptResponse],summary="恢复机构Prompt")
async def restore_org_prompt(
    base_prompt_id: int = Query(..., description="基础 Prompt ID"),
    organization_id: int = Query(..., description="机构 ID"),
    db: Session = Depends(get_db)
):
    result = await restore_base_prompt(db, base_prompt_id, organization_id)
    if not result:
        raise HTTPException(status_code=404, detail="Org prompt not found or system fallback missing")
    return GenericResponse(
        code=200,
        data=result,
        msg="恢复机构Prompt成功"
    )


# ==================== 个性化 Prompt (Overrides) ====================

@router.post("/override", response_model=GenericResponse[PromptOverrideResponse],summary="创建个性化Prompt")
async def create_override_prompt(
    prompt: PromptOverridesSchema,
    db: Session = Depends(get_db)
):
    result = await create_prompt_override(db, prompt)
    if not result:
        raise HTTPException(status_code=404, detail="Base prompt not found")
    return GenericResponse(
        code=200,
        data=result,
        msg="创建个性化Prompt成功"
    )


@router.post("/override/update", response_model=GenericResponse[PromptOverrideResponse],summary="更新个性化Prompt")
async def update_override_prompt(
    prompt: UpdatePromptOverridesSchema,
    db: Session = Depends(get_db)
):
    result = await update_prompt_override(db, prompt)
    if not result:
        raise HTTPException(status_code=404, detail="Override prompt not found")
    return GenericResponse(
        code=200,
        data=result,
        msg="更新个性化Prompt成功"
    )


@router.post("/override/delete", response_model=GenericResponse[dict],summary="删除个性化Prompt")
async def delete_override_prompt(
    prompt_id: int = Query(..., description="Override prompt ID"),
    db: Session = Depends(get_db)
):
    result = await delete_prompt_override(db, prompt_id)
    if not result:
        raise HTTPException(status_code=404, detail="Override prompt not found")
    return GenericResponse(
        code=200,
        data={"deleted_id": result.id},
        msg="删除个性化Prompt成功"
    )
