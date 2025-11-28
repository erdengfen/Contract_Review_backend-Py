"""
@Project ：Contract_Review_backend-Py 
@File    ：base.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/22 10:00 
"""
from typing import Generic, TypeVar, Optional,List
from pydantic import BaseModel, Field, ConfigDict
T = TypeVar('T')

class BaseSchema(BaseModel):

    code: Optional[int] = Field(200, description="状态码")
    msg: Optional[str] = Field("success", description="状态信息")
    data: Optional[dict] = Field(None, description="数据")


class GenericResponse(BaseSchema, Generic[T]):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    data: Optional[T] = Field(None, description="业务数据")



