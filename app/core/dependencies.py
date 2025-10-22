"""
@Project ：Contract_Review_backend-Py
@File    ：dependencies.py
@IDE     ：PyCharm
@Author  ：潘尚国
@Date    ：2025/10/22 09:41
"""
from app.core.mysql_db import SessionLocal


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()