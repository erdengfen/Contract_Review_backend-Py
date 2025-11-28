"""
@Project ：Contract_Review_backend-Py 
@File    ：prompt_manage.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/31 15:23 
"""
from typing import Optional

from pydantic import BaseModel, Field

# --------------system---------------------------
class SystemPromptResponse(BaseModel):
    id: int
    contract_type_id: int
    prompt_name: str
    prompt_text: str

    class Config:
        from_attributes = True  # Pydantic v2 兼容 ORM


class SystemPromptSchema(BaseModel):
    """
    创建基础 Prompt 模型
    """
    contract_type_id: Optional[int] =Field(None, description="合同类型id")
    prompt_name: Optional[str] = Field(..., description="Prompt 名称")
    prompt_content: Optional[str] = Field(..., description="Prompt 内容")


class UpdateSystemPromptSchema(BaseModel):
    """
    更新基础 Prompt 模型
    """
    id: Optional[int] =Field(None,description="系统Prompt ID")
    prompt_name: Optional[str] = Field(None, description="Prompt 名称")

    prompt_content: Optional[str] = Field(None, description="Prompt 内容")

# ---------base--------------------------------

class BasePromptResponse(BaseModel):
    id: int
    contract_type_id: int
    organization_id: int
    system_prompt_id: int
    prompt_name: str
    prompt_text: str
    is_override: int

    class Config:
        from_attributes = True


class BasePromptSchema(SystemPromptSchema):
    """
    创建Prompt 模型
        base_prompt_id = Column(Integer, comment="基础promptID")
    prompt_name = Column(String(255),comment="重写后的prompt名称")
    prompt_text = Column(Text,comment="重写后的prompt文本")
    is_override = Column(Integer,default=0,comment="是否重写基础prompt")
    created_at = Column(TIMESTAMP, default=datetime.now, comment="创建时间")
    """
    base_prompt_id: Optional[int] = Field(..., description="基础promptID")
    prompt_name: Optional[str] = Field(..., description="重写后的prompt名称")
    prompt_text: Optional[str] = Field(..., description="重写后的prompt文本")
    is_override: Optional[int] = Field(..., description="是否重写基础prompt")

class UpdateBasePromptSchema(BaseModel):
    """
    更新基础 Prompt 模型
    """
    base_prompt_id: Optional[int] = Field(..., description="基础promptID")
    organization_id: Optional[int] = Field(..., description="机构ID")
    prompt_name: Optional[str] = Field(None, description="重写后的prompt名称")
    prompt_text: Optional[str] = Field(None, description="重写后的prompt文本")

# -----------overrides------------------------------
class PromptOverrideResponse(BaseModel):
    id: int
    base_prompt_id: int
    organization_id: int
    override_name: str
    override_text: str

    class Config:
        from_attributes = True

class PromptOverridesSchema(BaseModel):
    """
    个性化prompt 模型
    """
    base_prompt_id: Optional[int] = Field(..., description="机构基础promptID")
    override_name: Optional[str] = Field(..., description="个性化prompt名称")
    override_text: Optional[str] = Field(..., description="重写后的prompt文本")

class UpdatePromptOverridesSchema(BaseModel):
    """
    更新个性化 Prompt 模型
    """
    id: Optional[int] = Field(..., description="个性化promptID")
    override_name: Optional[str] = Field(None, description="个性化prompt名称")
    override_text: Optional[str] = Field(None, description="重写后的prompt文本")


