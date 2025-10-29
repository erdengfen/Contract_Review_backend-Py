# 初始化 Redis 和 LLM 管理器
from app.core.llm_manager import LLMManager
from app.core.redis import RedisHandler

redis_handler = RedisHandler()
llm_manager = LLMManager(redis_handler)