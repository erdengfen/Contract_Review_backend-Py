"""
@Project ：Contract_Review_backend-Py 
@File    ：cas_server.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/27 16:58 
"""
from cas import CASClient
from app.config.config import settings


host=settings.cas_config.host_local
port=settings.cas_config.port
# 定义密钥和算法
SECRET_KEY = settings.cas_config.SECRET_KEY
ALGORITHM = settings.cas_config.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.cas_config.ACCESS_TOKEN_EXPIRE_MINUTES
service_url = f"http://{host}:{port}/cas_callback"

cas_client = CASClient(
    server_url="https://ids.cqupt.edu.cn/authserver/login",
    service_url=service_url,
    version=3,
)



