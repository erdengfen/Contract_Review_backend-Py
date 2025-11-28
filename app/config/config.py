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
    port: int = Field(8080, description="服务器端口")
    timeout: int = Field(60, description="请求超时时间（秒）")
    workers: int = Field(4, description="工作进程数")


class CASConfig(BaseModel):
    host_local: str = Field("0.0.0.0", description="本地CES主机地址")
    host_online: str = Field("agents.cqupt.edu.cn", description="线上CES主机地址")
    port: int = Field(8080, description="CES端口")
    SECRET_KEY: str = Field(..., description="JWT密钥")
    ALGORITHM: str = Field("HS256", description="JWT算法")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(60, description="访问令牌过期时间（分钟）")
    vanna_url_local: str = Field("172.22.182.17:8084", description="本地Vanna URL")
    vanna_url_online: str = Field("vanna:8084", description="线上Vanna URL")


class OpenAIConfig(BaseModel):
    # provider: str = Field("deepseek", description="LLM提供者，如 deepseek/openai")
    api_key: str = Field(..., description="LLM API密钥")
    model: str = Field("deepseek-chat", description="模型名称")
    api_base: str = Field("https://openai.deepseek.cn/v1", description="LLM API基础URL")


class DatabaseConfig(BaseModel):
    host: str = Field("localhost", description="数据库主机地址")
    port: int = Field(3306, description="数据库端口")
    name: str = Field("contract_review", description="数据库名称")
    username: str = Field("root", description="数据库用户名")
    password: str = Field("chongqinglingdong123456", description="数据库密码")
    pool_size: int = Field(10, description="数据库连接池大小")
    pool_timeout: int = Field(30, description="数据库连接池超时时间（秒）")

    def database_url(self) -> str:
        return f"mysql+pymysql://{self.username}:{self.password}@{self.host}:{self.port}/{self.name}"


class RedisConfig(BaseModel):
    host: str = Field("localhost", description="Redis主机地址")
    port: int = Field(6379, description="Redis端口")
    db: int = Field(10, description="Redis数据库索引")
    password: str = Field("chongqinglingdong123456", description="Redis密码")
    decode_responses: bool = Field(True, description="是否解码Redis响应")
    max_connections: int = Field(20, description="Redis最大连接数")
    socket_connect_timeout: int = Field(5, description="Redis连接超时时间（秒）")
    socket_timeout: int = Field(10, description="Redis操作超时时间（秒）")

class JWTConfig(BaseModel):
    secret_key: str = Field(..., description="JWT密钥")
    refresh_secret_key: str = Field(..., description="JWT刷新密钥")
    algorithm: str = Field("HS256", description="JWT算法")
    access_token_expire_minutes: int = Field(10080, description="访问令牌过期时间（分钟）")
    refresh_token_expire_days: int = Field(7, description="刷新令牌过期时间（天）")


class LoggingConfig(BaseModel):
    logger_name: str = Field("app_logger", description="日志记录器名称")
    log_dir: str = Field("logs", description="日志目录")
    log_file: str = Field("app.log", description="日志文件名")
    log_level: str = Field("INFO", description="日志级别")
    backup_days: int = Field(30, description="日志备份天数")
    encoding: str = Field("utf-8", description="日志编码")

class MCPConfig(BaseModel):
    url: str = Field(..., description="MCP服务器URL")



class Config(BaseModel):
    APP_NAME: str = Field("合同审阅系统API", description="应用名称")
    APP_VERSION: str = Field("1.0.0", description="应用版本")
    UPLOAD_DIR: str = Field("output/uploads", description="合同上传目录")
    OSS_BUCKET_DIR: str = Field("output/contract_files", description="合同文件存储目录")
    RESULTS_DIR: str = Field("output/results", description="合同审阅结果目录")
    SESSIONS_DIR: str = Field("output/sessions", description="会话目录")
    SESSION_TIMEOUT: int = Field(3600, description="会话超时时间（秒）")
    MAX_CONCURRENT_SESSIONS: int = Field(100, description="最大并发会话数")

    server: ServerConfig
    cas_config: CASConfig
    openai_config: OpenAIConfig
    database: DatabaseConfig
    redis_config: RedisConfig
    jwt_config: JWTConfig
    logging_config: LoggingConfig
    mcp_server: MCPConfig



def load_config(config_path=BASE_DIR / "app" / "config" / "config.yaml"):

    with open(config_path, "r", encoding="utf-8") as f:
        raw_config = yaml.safe_load(f)
    return Config.model_validate(raw_config)


settings = load_config()