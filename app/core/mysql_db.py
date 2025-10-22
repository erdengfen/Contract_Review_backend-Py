"""
@Project ：Contract_Review_backend-Py 
@File    ：mysql_db.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/22 09:33 
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config.config import settings


engine = create_engine(settings.database.database_url())

Base = declarative_base()
# 自动创建表结构
Base.metadata.create_all(bind=engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

