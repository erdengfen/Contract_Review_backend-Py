import redis
from app.config.config import settings

class RedisClient:
    _instance = None
    _pool = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls) #实际分配一个新对象的内存空间。若重写__new__而不写这句则不会创建对象
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
                # password=settings.redis_config.password,
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

class RedisHandler:
    """
    Redis 操作类，封装常用的 Redis 操作方法
    """
    def __init__(self):
        self.client = RedisClient.get_instance()

    def set(self, key: str, value: str, ex: int = None):
        """
        设置键值对
        :param key: 键
        :param value: 值
        :param ex: 过期时间（秒）
        :return: 设置成功返回 True，失败返回 False
        """
        try:
            self.client.set(key, value, ex=ex)
            return True
        except Exception as e:
            print(f"Redis set error: {e}")
            return False

    def get(self, key: str) -> str:
        """
        获取键对应的值
        :param key: 键
        :return: 键对应的值，如果键不存在返回 None
        """
        try:
            return self.client.get(key)
        except Exception as e:
            print(f"Redis get error: {e}")
            return None

    def delete(self, key: str) -> int:
        """
        删除键值对
        :param key: 键
        :return: 删除成功返回删除的键的数量，失败返回 0
        """
        try:
            return self.client.delete(key)
        except Exception as e:
            print(f"Redis delete error: {e}")
            return 0

    def exists(self, key: str) -> bool:
        """
        检查键是否存在
        :param key: 键
        :return: 键存在返回 True，不存在返回 False
        """
        try:
            return self.client.exists(key) > 0
        except Exception as e:
            print(f"Redis exists error: {e}")
            return False

    def expire(self, key: str, ex: int) -> bool:
        """
        设置键的过期时间
        :param key: 键
        :param ex: 过期时间（秒）
        :return: 设置成功返回 True，失败返回 False
        """
        try:
            return self.client.expire(key, ex)
        except Exception as e:
            print(f"Redis expire error: {e}")
            return False
