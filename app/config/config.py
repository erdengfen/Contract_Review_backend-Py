"""
@Project ：Contract_Review_backend-Py 
@File    ：config.py.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/22 09:08 
"""
from pydantic import BaseModel, Field
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class ServerConfig(BaseModel):

    host: str = Field("0.0.0.0", description="服务器主机地址")
    port: int = Field(8081, description="服务器端口")
    timeout: int = Field(60, description="请求超时时间（秒）")
    workers: int = Field(4, description="工作进程数")


class OpenAIConfig(BaseModel):
    api_key: str = Field(..., description="OpenAI API密钥")
    model: str = Field("gpt-3.5-turbo", description="OpenAI模型名称")



class DatabaseConfig(BaseModel):
    host: str = Field("localhost", description="数据库主机地址")
    port: int = Field(27017, description="数据库端口")
    name: str = Field("contract_review", description="数据库名称")
    username: str = Field("admin", description="数据库用户名")
    password: str = Field("admin123", description="数据库密码")
    pool_size: int = Field(10, description="数据库连接池大小")
    pool_timeout: int = Field(30, description="数据库连接池超时时间（秒）")

    def database_url(self) -> str:
        return f"mysql+pymysql://{self.username}:{self.password}@{self.host}:{self.port}/{self.name}"


class RedisConfig(BaseModel):
    host: str = Field("localhost", description="Redis主机地址")
    port: int = Field(6379, description="Redis端口")
    db: int = Field(0, description="Redis数据库索引")
    password: str = Field(None, description="Redis密码")
    decode_responses: bool = Field(True, description="是否解码Redis响应")
    max_connections: int = Field(20, description="Redis最大连接数")
    socket_connect_timeout: int = Field(5, description="Redis连接超时时间（秒）")
    socket_timeout: int = Field(10, description="Redis操作超时时间（秒）")

class Config(BaseModel):
    server: ServerConfig
    openai_config: OpenAIConfig
    database: DatabaseConfig
    redis_config: RedisConfig


def load_config(config_path=BASE_DIR / "app" / "config" / "config.yaml"):

    with open(config_path, "r", encoding="utf-8") as f:
        raw_config = yaml.safe_load(f)
    return Config.model_validate(raw_config)


settings = load_config()