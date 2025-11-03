"""
@Project ：Contract_Review_backend-Py 
@File    ：prompt.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/30 16:18 
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, TIMESTAMP, Text

from app.core.mysql_db import Base


    # 这里可能还有其他字段需要梳理一下

class SystemPrompt(Base):
    """
    基础prompt表
    """
    __tablename__ = "system_prompts"
    id = Column(Integer, primary_key=True,comment="提示promptID")
    contract_type_id = Column(Integer,comment="合同类型ID")
    prompt_name = Column(String(255),comment="提示prompt名称")
    prompt_text = Column(Text,comment="提示prompt文本")
    created_at = Column(TIMESTAMP, default=datetime.now, comment="创建时间")
    updated_at = Column(TIMESTAMP, default=datetime.now, onupdate=datetime.now, comment="更新时间")


class BasePrompt(Base):
    """
    机构prompt表主要记录重写后的prompt文本
    """
    __tablename__ = "base_prompts"
    id = Column(Integer, primary_key=True,comment="ID")
    contract_type_id = Column(Integer,comment="合同类型ID")
    organization_id = Column(Integer,comment="机构ID")
    system_prompt_id = Column(Integer, comment="系统promptID")
    prompt_name = Column(String(255),comment="重写后的prompt名称")
    prompt_text = Column(Text,comment="重写后的prompt文本")
    is_override = Column(Integer,default=0,comment="是否重写基础prompt")
    created_at = Column(TIMESTAMP, default=datetime.now, comment="创建时间")
    updated_at = Column(TIMESTAMP, default=datetime.now, onupdate=datetime.now, comment="更新时间")


# --------------------个性化prompt------------------------------------------------
class PromptOverrides(Base):
    """
    机构个性化 Prompt 表
    """
    __tablename__ = "prompt_overrides"
    id = Column(Integer, primary_key=True,comment="ID")
    system_base_prompt_id = Column(Integer,comment="基础promptID")
    override_name = Column(String(255),comment="个性化prompt名称")
    override_text = Column(Text,comment="个性化prompt文本")
    created_at = Column(TIMESTAMP, default=datetime.now, comment="创建时间")
    updated_at = Column(TIMESTAMP, default=datetime.now, onupdate=datetime.now, comment="更新时间")


