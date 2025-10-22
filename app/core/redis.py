import redis
from app.config.config import settings

class RedisClient:
    _instance = None
    _pool = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            # 初始化连接池（惰性加载）
            cls._pool = None
        return cls._instance

    @classmethod
    def get_pool(cls) -> redis.ConnectionPool:
        """获取连接池（懒加载）"""
        if not cls._pool:
            cls._pool = redis.ConnectionPool(
                host=settings.redis_config.host,
                port=settings.redis_config.port,
                password=settings.redis_config.password,
                db=settings.redis_config.db,
                decode_responses=settings.redis_config.decode_responses,
                max_connections=settings.redis_config.max_connections,
                socket_connect_timeout=settings.redis_config.socket_connect_timeout,
                socket_timeout=settings.redis_config.socket_timeout
            )
        return cls._pool

    @classmethod
    def get_instance(cls) -> redis.Redis:
        """获取Redis操作实例"""
        return redis.Redis(connection_pool=cls.get_pool())

    @classmethod
    def close_pool(cls):
        """关闭连接池"""
        if cls._pool:
            cls._pool.disconnect()
            cls._pool = None
            cls._instance = None

def get_redis() -> redis.Redis:
    return RedisClient.get_instance()