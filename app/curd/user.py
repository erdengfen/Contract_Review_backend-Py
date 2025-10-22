"""
@Project ：Contract_Review_backend-Py 
@File    ：user.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/22 09:52 
"""
from sqlalchemy.orm import Session

from app.core.mysql_db import SessionLocal
from app.models.user import User



def get_user(db: Session, user_id: int):
    user = db.query(User).filter(User.user_id == user_id).first()
    return user
