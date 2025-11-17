import asyncio
import json
from .llm import init_llm
from .redis import RedisHandler
from ..models.user import UserLLMConfig


class LLMManager:
    """负责管理多用户 LLM 实例"""
    _instances = {}
    _lock = asyncio.Lock()

    def __init__(self, redis_handler: RedisHandler):
        self.redis = redis_handler

    async def get_user_llm(self, user_id: int, db_session):
        """获取用户当前选中的 LLM 实例"""
        # 1. 获取当前选中模型名
        active_model = self.redis.get(f"user:active_model:{user_id}")
        if not active_model:
            # 数据库查找
            user_cfg = db_session.query(UserLLMConfig).filter_by(user_id=user_id, is_active=True).first()
            if not user_cfg:
                raise ValueError("用户未选择当前模型")
            active_model = user_cfg.model_name
            self.redis.set(f"user:active_model:{user_id}", active_model, ex=3600)

        key = (user_id, active_model)
        if key in self._instances:
            return self._instances[key]

        # 2. 获取模型配置
        cache_key = f"user:llm_config:{user_id}"
        cached = self.redis.get(cache_key)
        if cached:
            config_list = json.loads(cached)
        else:
            configs = db_session.query(UserLLMConfig).filter_by(user_id=user_id).all()
            if not configs:
                raise ValueError("用户未配置任何模型")
            config_list = [self._serialize_model(c) for c in configs]
            self.redis.set(cache_key, json.dumps(config_list), ex=3600)

        config = next((c for c in config_list if c["model_name"] == active_model), None)
        if not config:
            raise ValueError("当前选中模型配置不存在")

        # 3. 异步锁 + 初始化
        async with self._lock:
            if key not in self._instances:
                llm_instance = init_llm(
                    api_key=config["api_key"],
                    model=config["model_name"],
                    base_url=config["base_url"]
                )
                self._instances[key] = llm_instance

        return self._instances[key]

    async def set_user_llm_config(self, db_session, user_id: int, api_key: str, model_name: str,
                                  model_provider: str = "deepseek", base_url: str = None):
        """新增或更新用户模型配置"""
        existing = db_session.query(UserLLMConfig).filter_by(user_id=user_id, model_name=model_name).first()
        if existing:
            existing.api_key = api_key
            existing.model_provider = model_provider
            existing.base_url = base_url
        else:
            new_model = UserLLMConfig(
                user_id=user_id,
                api_key=api_key,
                model_name=model_name,
                model_provider=model_provider,
                base_url=base_url
            )
            db_session.add(new_model)
        db_session.commit()

        # 清理缓存和内存实例
        await self.clear_user_llm_cache(user_id, model_name)

    async def set_active_model(self, user_id: int, model_name: str, db_session):
        """用户切换当前使用模型"""
        # 数据库更新
        db_session.query(UserLLMConfig).filter_by(user_id=user_id).update({"is_active": False})
        updated = db_session.query(UserLLMConfig).filter_by(user_id=user_id, model_name=model_name).update(
            {"is_active": True})
        if not updated:
            raise ValueError("用户未配置该模型")
        db_session.commit()

        # Redis 更新
        self.redis.set(f"user:active_model:{user_id}", model_name, ex=3600)
        await self.clear_user_llm_cache(user_id, model_name)

    async def clear_user_llm_cache(self, user_id: int, model_name: str = None):
        """清理内存和redis缓存"""
        key = (user_id, model_name or "__default__")
        async with self._lock:
            self._instances.pop(key, None)
        self.redis.delete(f"user:llm_config:{user_id}")

    @staticmethod
    def _serialize_model(model: UserLLMConfig):
        """将 ORM 模型对象转字典"""
        return {
            "api_key": model.api_key,
            "model_name": model.model_name,
            "provider": model.model_provider,
            "base_url": model.base_url
        }

