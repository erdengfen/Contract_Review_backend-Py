"""
@Project ：Contract_Review_backend-Py
@File    ：dependencies.py
@IDE     ：PyCharm
@Author  ：潘尚国
@Date    ：2025/10/22 09:41
"""
from sqlalchemy.orm import sessionmaker

from app.core.mysql_db import Base, engine
import app.models
# 自动创建表结构
Base.metadata.create_all(bind=engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()