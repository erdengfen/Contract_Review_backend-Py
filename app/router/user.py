"""
@Project ：Contract_Review_backend-Py 
@File    ：user.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/22 09:52 
"""
from fastapi import Depends, APIRouter, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.curd.user import get_user
from  app.schemas.base import GenericResponse
from app.schemas.user import UserResponse
router = APIRouter()



@router.get("/get_user/{user_id}", response_model=GenericResponse[UserResponse])
def read_user(user_id: int, db: Session = Depends(get_db)):
    """
    获取用户信息
    :param user_id:
    :param db:
    :return:
    """
    user = get_user(db, user_id=user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return GenericResponse[UserResponse](data=user)
