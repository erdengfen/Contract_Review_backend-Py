"""
增强记忆服务 - 支持多用户并发和审阅上下文管理
"""
import logging
import json
import redis
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import asyncio

from ..core.database import DatabaseManager
from ..core.config import REDIS_URL, SESSION_TIMEOUT
from ..utils.content_slicer import split_text_by_length

logger = logging.getLogger(__name__)

class EnhancedMemoryService:
    """记忆服务 - 支持多用户并发和审阅上下文"""
    
    def __init__(self, db_manager: DatabaseManager, redis_url: str = None):
        self.db = db_manager
        self.redis_client = redis.from_url(redis_url or REDIS_URL, decode_responses=True)
        self.session_timeout = SESSION_TIMEOUT

        
    def _get_redis_key(self, user_id: str, session_id: str, key_type: str = "session") -> str:
        """生成Redis键名"""
        return f"contract_review:{user_id}:{session_id}:{key_type}"
    
    def _get_context_key(self, user_id: str, session_id: str, chunk_index: int) -> str:
        """生成审阅上下文键名"""
        return f"contract_review:{user_id}:{session_id}:context:{chunk_index}"
    
    async def get_or_create_user_session(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """获取或创建用户会话（支持多用户隔离）"""
        try:
            # 首先尝试从Redis缓存获取
            cache_key = self._get_redis_key(user_id, session_id, "session")
            cached_session = self.redis_client.get(cache_key)
            
            if cached_session:
                session_data = json.loads(cached_session)
                # 更新访问时间
                self.redis_client.expire(cache_key, self.session_timeout)
                logger.info(f"从缓存获取会话: {user_id}/{session_id}")
                return session_data
            
            # 从数据库获取
            session_data = self.db.get_user_session(user_id, session_id)
            
            if session_data:
                # 缓存到Redis
                self.redis_client.setex(
                    cache_key, 
                    self.session_timeout, 
                    json.dumps(session_data, ensure_ascii=False)
                )
                logger.info(f"从数据库获取会话: {user_id}/{session_id}")
                return session_data
            
            # 创建新会话
            new_session = {
                "user_id": user_id,
                "session_id": session_id,
                "dialogue_history": [],
                "contract_path": "",
                "contract_content": "",
                "modifications": [],
                "selected_mod_indices": [],
                "modified_contract_path": "",
                "report_path": "",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # 保存到数据库和缓存
            if self.db.save_user_session(user_id, session_id, new_session):
                self.redis_client.setex(
                    cache_key, 
                    self.session_timeout, 
                    json.dumps(new_session, ensure_ascii=False)
                )
                logger.info(f"创建新会话: {user_id}/{session_id}")
                return new_session
            else:
                logger.error(f"创建会话失败: {user_id}/{session_id}")
                return new_session
                
        except Exception as e:
            logger.error(f"获取用户会话失败: {e}")
            return self._create_default_session(user_id, session_id)
    
    def _create_default_session(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """创建默认会话"""
        return {
            "user_id": user_id,
            "session_id": session_id,
            "dialogue_history": [],
            "contract_path": "",
            "contract_content": "",
            "modifications": [],
            "selected_mod_indices": [],
            "modified_contract_path": "",
            "report_path": "",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
    
    async def update_user_session(self, user_id: str, session_id: str, updates: Dict[str, Any]) -> bool:
        """更新用户会话"""
        try:
            # 获取当前会话
            session = await self.get_or_create_user_session(user_id, session_id)
            
            # 更新数据
            session.update(updates)
            session["updated_at"] = datetime.now().isoformat()
            
            # 保存到数据库
            success = self.db.save_user_session(user_id, session_id, session)
            
            if success:
                # 更新Redis缓存
                cache_key = self._get_redis_key(user_id, session_id, "session")
                self.redis_client.setex(
                    cache_key, 
                    self.session_timeout, 
                    json.dumps(session, ensure_ascii=False)
                )
                logger.info(f"更新会话成功: {user_id}/{session_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"更新用户会话失败: {e}")
            return False
    
    async def save_contract_chunks(self, user_id: str, session_id: str, contract_content: str) -> List[Dict[str, Any]]:
        """保存合同分块（支持多用户隔离）"""
        try:
            # 分割合同内容
            chunks = split_text_by_length(contract_content, max_length=4000)
            
            # 保存到数据库
            saved_chunks = []
            for idx, chunk_content in enumerate(chunks):
                chunk_data = {
                    "chunk_index": idx,
                    "chunk_content": chunk_content,
                    "chunk_summary": self._generate_chunk_summary(chunk_content),
                    "review_result": ""
                }
                
                # 保存到数据库
                self.db.save_contract_chunk(
                    user_id, session_id, idx, 
                    chunk_content, chunk_data["chunk_summary"]
                )
                
                # 缓存到Redis
                context_key = self._get_context_key(user_id, session_id, idx)
                self.redis_client.setex(
                    context_key, 
                    self.session_timeout, 
                    json.dumps(chunk_data, ensure_ascii=False)
                )
                
                saved_chunks.append(chunk_data)
            
            logger.info(f"保存合同分块成功: {user_id}/{session_id}, 共{len(chunks)}块")
            return saved_chunks
            
        except Exception as e:
            logger.error(f"保存合同分块失败: {e}")
            return []
    
    def _generate_chunk_summary(self, chunk_content: str) -> str:
        """生成分块摘要"""
        # 简单的摘要生成，可以后续优化
        if len(chunk_content) > 200:
            return chunk_content[:200] + "..."
        return chunk_content
    
    async def build_review_context(self, user_id: str, session_id: str, current_chunk_index: int) -> str:
        """构建审阅上下文（解决断章取义问题）"""
        try:
            context_parts = []
            
            # 1. 获取合同整体信息
            session = await self.get_or_create_user_session(user_id, session_id)
            if session.get("contract_content"):
                # 添加合同基本信息
                context_parts.append("## 合同基本信息")
                context_parts.append(f"甲方: {session.get('party_a', '未知')}")
                context_parts.append(f"乙方: {session.get('party_b', '未知')}")
                context_parts.append("")
            
            # 2. 获取前面分块的审阅结果
            previous_reviews = await self._get_previous_reviews(user_id, session_id, current_chunk_index)
            if previous_reviews:
                context_parts.append("## 前面分块的审阅结果")
                for review in previous_reviews:
                    context_parts.append(f"### 第{review['chunk_index'] + 1}段审阅要点")
                    context_parts.append(f"主要问题: {review.get('summary', '无')}")
                    context_parts.append(f"风险等级: {review.get('risk_level', '未知')}")
                    context_parts.append("")
            
            # 3. 获取当前分块的前后文
            surrounding_context = await self._get_surrounding_context(user_id, session_id, current_chunk_index)
            if surrounding_context:
                context_parts.append("## 当前分块上下文")
                context_parts.append(surrounding_context)
                context_parts.append("")
            
            # 4. 添加审阅指导
            context_parts.append("## 审阅指导")
            context_parts.append("请结合上述上下文信息，确保审阅的连续性和一致性。")
            context_parts.append("特别注意与前面分块中已识别问题的关联性。")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"构建审阅上下文失败: {e}")
            return ""
    
    async def _get_previous_reviews(self, user_id: str, session_id: str, current_chunk_index: int) -> List[Dict[str, Any]]:
        """获取前面分块的审阅结果"""
        try:
            previous_reviews = []
            
            for i in range(current_chunk_index):
                # 尝试从Redis获取
                context_key = self._get_context_key(user_id, session_id, i)
                cached_data = self.redis_client.get(context_key)
                
                if cached_data:
                    chunk_data = json.loads(cached_data)
                    if chunk_data.get("review_result"):
                        # 解析审阅结果
                        review_summary = self._extract_review_summary(chunk_data["review_result"])
                        previous_reviews.append({
                            "chunk_index": i,
                            "summary": review_summary["summary"],
                            "risk_level": review_summary["risk_level"],
                            "key_issues": review_summary["key_issues"]
                        })
                else:
                    # 从数据库获取
                    chunks = self.db.get_contract_chunks(user_id, session_id)
                    for chunk in chunks:
                        if chunk["chunk_index"] == i and chunk.get("review_result"):
                            review_summary = self._extract_review_summary(chunk["review_result"])
                            previous_reviews.append({
                                "chunk_index": i,
                                "summary": review_summary["summary"],
                                "risk_level": review_summary["risk_level"],
                                "keys_issues": review_summary["keys_issues"]

                            })
                            break
            
            return previous_reviews
            
        except Exception as e:
            logger.error(f"获取前面审阅结果失败: {e}")
            return []
    
    async def _get_surrounding_context(self, user_id: str, session_id: str, current_chunk_index: int) -> str:
        """获取当前分块的前后文"""
        try:
            context_parts = []
            
            # 获取前一个分块的后半部分
            if current_chunk_index > 0:
                prev_chunk = await self._get_chunk_content(user_id, session_id, current_chunk_index - 1)
                if prev_chunk:
                    # 取后半部分作为上文
                    prev_half = prev_chunk[-500:] if len(prev_chunk) > 500 else prev_chunk
                    context_parts.append(f"上文: {prev_half}")
            
            # 获取后一个分块的前半部分
            next_chunk = await self._get_chunk_content(user_id, session_id, current_chunk_index + 1)
            if next_chunk:
                # 取前半部分作为下文
                next_half = next_chunk[:500] if len(next_chunk) > 500 else next_chunk
                context_parts.append(f"下文: {next_half}")


            
            return "\n\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"获取前后文失败: {e}")
            return ""
    
    async def _get_chunk_content(self, user_id: str, session_id: str, chunk_index: int) -> Optional[str]:
        """获取分块内容"""
        try:
            # 尝试从Redis获取
            context_key = self._get_context_key(user_id, session_id, chunk_index)
            cached_data = self.redis_client.get(context_key)
            
            if cached_data:
                chunk_data = json.loads(cached_data)
                return chunk_data.get("chunk_content")
            
            # 从数据库获取
            chunks = self.db.get_contract_chunks(user_id, session_id)
            for chunk in chunks:
                if chunk["chunk_index"] == chunk_index:
                    return chunk["chunk_content"]
            
            return None
            
        except Exception as e:
            logger.error(f"获取分块内容失败: {e}")
            return None
    
    def _extract_review_summary(self, review_result: str) -> Dict[str, Any]:
        """提取审阅结果摘要"""
        try:
            # 简单的摘要提取，可以后续优化
            import re
            
            # 提取风险等级
            risk_level_match = re.search(r'风险等级[：:]\s*([高|中|低])', review_result)
            risk_level = risk_level_match.group(1) if risk_level_match else "未知"
            
            # 提取关键问题
            key_issues = []
            issue_matches = re.findall(r'【修改点\d+】[^\n]*', review_result)
            key_issues = [match.strip() for match in issue_matches[:3]]  # 最多3个关键问题
            
            # 生成摘要
            summary = f"发现{len(key_issues)}个潜在问题，风险等级: {risk_level}"
            
            return {
                "summary": summary,
                "risk_level": risk_level,
                "key_issues": key_issues
            }
            
        except Exception as e:
            logger.error(f"提取审阅摘要失败: {e}")
            return {
                "summary": "审阅结果解析失败",
                "risk_level": "未知",
                "key_issues": []
            }
    
    async def save_review_result(self, user_id: str, session_id: str, chunk_index: int, review_result: str) -> bool:
        """保存审阅结果"""
        try:
            # 保存到数据库
            success = self.db.save_contract_chunk(
                user_id, session_id, chunk_index, 
                "", "", review_result
            )
            
            if success:
                # 更新Redis缓存
                context_key = self._get_context_key(user_id, session_id, chunk_index)
                cached_data = self.redis_client.get(context_key)
                
                if cached_data:
                    chunk_data = json.loads(cached_data)
                    chunk_data["review_result"] = review_result
                    self.redis_client.setex(
                        context_key, 
                        self.session_timeout, 
                        json.dumps(chunk_data, ensure_ascii=False)
                    )
                
                logger.info(f"保存审阅结果成功: {user_id}/{session_id}, 分块{chunk_index}")
            
            return success
            
        except Exception as e:
            logger.error(f"保存审阅结果失败: {e}")
            return False
    
    async def cleanup_expired_sessions(self) -> int:
        """清理过期会话"""
        try:
            # 清理Redis中的过期会话
            pattern = "contract_review:*:session"
            keys = self.redis_client.keys(pattern)
            
            cleaned_count = 0
            for key in keys:
                ttl = self.redis_client.ttl(key)
                if ttl == -1:  # 没有设置过期时间
                    self.redis_client.delete(key)
                    cleaned_count += 1
            
            logger.info(f"清理过期会话完成，共清理{cleaned_count}个")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"清理过期会话失败: {e}")
            return 0
    
    async def get_user_active_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户活跃会话列表"""
        try:
            # 从Redis获取活跃会话
            pattern = f"contract_review:{user_id}:*:session"
            keys = self.redis_client.keys(pattern)
            
            sessions = []
            for key in keys:
                session_data = self.redis_client.get(key)
                if session_data:
                    session = json.loads(session_data)
                    sessions.append({
                        "session_id": session["session_id"],
                        "created_at": session["created_at"],
                        "updated_at": session["updated_at"],
                        "has_contract": bool(session.get("contract_path")),
                        "modifications_count": len(session.get("modifications", [])),
                        "party_a": session.get("party_a", ""),
                        "party_b": session.get("party_b", "")
                    })
            
            # 按更新时间排序
            sessions.sort(key=lambda x: x["updated_at"], reverse=True)
            return sessions
            
        except Exception as e:
            logger.error(f"获取用户活跃会话失败: {e}")
            return []
