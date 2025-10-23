# """
# 数据库管理模块
# """
# import sqlite3
# import json
# import logging
# from pathlib import Path
# from typing import Dict, List, Any, Optional
# from datetime import datetime
#
# logger = logging.getLogger(__name__)
#
# class DatabaseManager:
#     """数据库管理器"""
#
#     def __init__(self, db_path: str = "data/contract_review.db"):
#         self.db_path = Path(db_path)
#         self.db_path.parent.mkdir(parents=True, exist_ok=True)
#         self.init_database()
#
#     def init_database(self):
#         """初始化数据库表"""
#         try:
#             with sqlite3.connect(self.db_path) as conn:
#                 cursor = conn.cursor()
#
#                 # 用户会话表
#                 cursor.execute("""
#                     CREATE TABLE IF NOT EXISTS user_sessions (
#                         id INTEGER PRIMARY KEY AUTOINCREMENT,
#                         user_id TEXT NOT NULL,
#                         session_id TEXT NOT NULL,
#                         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#                         updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#                         contract_path TEXT,
#                         document_id TEXT,
#                         party_a TEXT,
#                         party_b TEXT,
#                         contract_content TEXT,
#                         dialogue_history TEXT,
#                         modifications TEXT,
#                         selected_mod_indices TEXT,
#                         modified_contract_path TEXT,
#                         report_path TEXT,
#                         UNIQUE(user_id, session_id)
#                     )
#                 """)
#
#                 # 合同分块表
#                 cursor.execute("""
#                     CREATE TABLE IF NOT EXISTS contract_chunks (
#                         id INTEGER PRIMARY KEY AUTOINCREMENT,
#                         user_id TEXT NOT NULL,
#                         session_id TEXT NOT NULL,
#                         chunk_index INTEGER NOT NULL,
#                         chunk_content TEXT NOT NULL,
#                         chunk_summary TEXT,
#                         review_result TEXT,
#                         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#                         UNIQUE(user_id, session_id, chunk_index)
#                     )
#                 """)
#
#                 # 审阅上下文表
#                 cursor.execute("""
#                     CREATE TABLE IF NOT EXISTS review_context (
#                         id INTEGER PRIMARY KEY AUTOINCREMENT,
#                         user_id TEXT NOT NULL,
#                         session_id TEXT NOT NULL,
#                         context_type TEXT NOT NULL, -- 'contract_summary', 'previous_reviews', 'key_terms'
#                         context_data TEXT NOT NULL,
#                         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#                     )
#                 """)
#
#                 conn.commit()
#                 logger.info("数据库初始化完成")
#
#         except Exception as e:
#             logger.error(f"数据库初始化失败: {e}")
#             raise
#
#     def get_connection(self):
#         """获取数据库连接"""
#         return sqlite3.connect(self.db_path)
#
#     def save_user_session(self, user_id: str, session_id: str, session_data: Dict[str, Any]) -> bool:
#         """保存用户会话"""
#         try:
#             with self.get_connection() as conn:
#                 cursor = conn.cursor()
#
#                 # 准备数据
#                 data = {
#                     'user_id': user_id,
#                     'session_id': session_id,
#                     'contract_path': session_data.get('contract_path', ''),
#                     'document_id': session_data.get('document_id', ''),
#                     'party_a': session_data.get('party_a', ''),
#                     'party_b': session_data.get('party_b', ''),
#                     'contract_content': session_data.get('contract_content', ''),
#                     'dialogue_history': json.dumps(session_data.get('dialogue_history', []), ensure_ascii=False),
#                     'modifications': json.dumps(session_data.get('modifications', []), ensure_ascii=False),
#                     'selected_mod_indices': json.dumps(session_data.get('selected_mod_indices', []), ensure_ascii=False),
#                     'modified_contract_path': session_data.get('modified_contract_path', ''),
#                     'report_path': session_data.get('report_path', ''),
#                     'updated_at': datetime.now().isoformat()
#                 }
#
#                 # 插入或更新
#                 cursor.execute("""
#                     INSERT OR REPLACE INTO user_sessions
#                     (user_id, session_id, contract_path, document_id, party_a, party_b,
#                      contract_content, dialogue_history, modifications, selected_mod_indices,
#                      modified_contract_path, report_path, updated_at)
#                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#                 """, tuple(data.values()))
#
#                 conn.commit()
#                 return True
#
#
#         except Exception as e:
#             logger.error(f"保存用户会话失败: {e}")
#             return False
#
#     def get_user_session(self, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
#         """获取用户会话"""
#         try:
#             with self.get_connection() as conn:
#                 cursor = conn.cursor()
#                 cursor.execute("""
#                     SELECT * FROM user_sessions
#                     WHERE user_id = ? AND session_id = ?
#                 """, (user_id, session_id))
#
#                 row = cursor.fetchone()
#                 if not row:
#                     return None
#
#                 # 转换列名
#                 columns = [desc[0] for desc in cursor.description]
#                 session_data = dict(zip(columns, row))
#
#                 # 解析JSON字段
#                 session_data['dialogue_history'] = json.loads(session_data.get('dialogue_history', '[]'))
#                 session_data['modifications'] = json.loads(session_data.get('modifications', '[]'))
#                 session_data['selected_mod_indices'] = json.loads(session_data.get('selected_mod_indices', '[]'))
#
#                 return session_data
#
#         except Exception as e:
#             logger.error(f"获取用户会话失败: {e}")
#             return None
#
#     def save_contract_chunk(self, user_id: str, session_id: str, chunk_index: int,
#                           chunk_content: str, chunk_summary: str = "",
#                           review_result: str = "") -> bool:
#         """保存合同分块"""
#         try:
#             with self.get_connection() as conn:
#                 cursor = conn.cursor()
#                 cursor.execute("""
#                     INSERT OR REPLACE INTO contract_chunks
#                     (user_id, session_id, chunk_index, chunk_content, chunk_summary, review_result)
#                     VALUES (?, ?, ?, ?, ?, ?)
#                 """, (user_id, session_id, chunk_index, chunk_content, chunk_summary, review_result))
#
#                 conn.commit()
#                 return True
#
#         except Exception as e:
#             logger.error(f"保存合同分块失败: {e}")
#             return False
#
#     def get_contract_chunks(self, user_id: str, session_id: str) -> List[Dict[str, Any]]:
#         """获取合同分块列表"""
#         try:
#             with self.get_connection() as conn:
#                 cursor = conn.cursor()
#                 cursor.execute("""
#                     SELECT * FROM contract_chunks
#                     WHERE user_id = ? AND session_id = ?
#                     ORDER BY chunk_index
#                 """, (user_id, session_id))
#
#                 columns = [desc[0] for desc in cursor.description]
#                 return [dict(zip(columns, row)) for row in cursor.fetchall()]
#
#         except Exception as e:
#             logger.error(f"获取合同分块失败: {e}")
#             return []
#
#     def save_review_context(self, user_id: str, session_id: str, context_type: str,
#                           context_data: Dict[str, Any]) -> bool:
#         """保存审阅上下文"""
#         try:
#             with self.get_connection() as conn:
#                 cursor = conn.cursor()
#                 cursor.execute("""
#                     INSERT INTO review_context
#                     (user_id, session_id, context_type, context_data)
#                     VALUES (?, ?, ?, ?)
#                 """, (user_id, session_id, context_type, json.dumps(context_data, ensure_ascii=False)))
#
#                 conn.commit()
#                 return True
#
#         except Exception as e:
#             logger.error(f"保存审阅上下文失败: {e}")
#             return False
#
#     def get_review_context(self, user_id: str, session_id: str, context_type: str = None) -> List[Dict[str, Any]]:
#         """获取审阅上下文"""
#         try:
#             with self.get_connection() as conn:
#                 cursor = conn.cursor()
#
#                 if context_type:
#                     cursor.execute("""
#                         SELECT * FROM review_context
#                         WHERE user_id = ? AND session_id = ? AND context_type = ?
#                         ORDER BY created_at DESC
#                     """, (user_id, session_id, context_type))
#                 else:
#                     cursor.execute("""
#                         SELECT * FROM review_context
#                         WHERE user_id = ? AND session_id = ?
#                         ORDER BY created_at DESC
#                     """, (user_id, session_id))
#
#                 columns = [desc[0] for desc in cursor.description]
#                 results = []
#                 for row in cursor.fetchall():
#                     data = dict(zip(columns, row))
#                     data['context_data'] = json.loads(data['context_data'])
#                     results.append(data)
#
#                 return results
#
#         except Exception as e:
#             logger.error(f"获取审阅上下文失败: {e}")
#             return []
#
#     def delete_user_session(self, user_id: str, session_id: str) -> bool:
#         """删除用户会话及其相关数据"""
#         try:
#             with self.get_connection() as conn:
#                 cursor = conn.cursor()
#
#                 # 删除相关数据
#                 cursor.execute("DELETE FROM user_sessions WHERE user_id = ? AND session_id = ?", (user_id, session_id))
#                 cursor.execute("DELETE FROM contract_chunks WHERE user_id = ? AND session_id = ?", (user_id, session_id))
#                 cursor.execute("DELETE FROM review_context WHERE user_id = ? AND session_id = ?", (user_id, session_id))
#
#                 conn.commit()
#                 return True
#
#         except Exception as e:
#             logger.error(f"删除用户会话失败: {e}")
#             return False
#
#     def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
#         """获取用户的所有会话"""
#         try:
#             with self.get_connection() as conn:
#                 cursor = conn.cursor()
#                 cursor.execute("""
#                     SELECT session_id, created_at, updated_at, contract_path,
#                            party_a, party_b, modifications
#                     FROM user_sessions
#                     WHERE user_id = ?
#                     ORDER BY updated_at DESC
#                 """, (user_id,))
#
#                 columns = [desc[0] for desc in cursor.description]
#                 sessions = []
#                 for row in cursor.fetchall():
#                     session = dict(zip(columns, row))
#                     # 解析修改建议数量
#                     try:
#                         modifications = json.loads(session.get('modifications', '[]'))
#                         session['modifications_count'] = len(modifications)
#                     except:
#                         session['modifications_count'] = 0
#                     sessions.append(session)
#
#                 return sessions
#
#         except Exception as e:
#             logger.error(f"获取用户会话列表失败: {e}")
#             return []
#
#     def cleanup_old_sessions(self, days: int = 30) -> int:
#         """清理旧会话数据"""
#         try:
#             with self.get_connection() as conn:
#                 cursor = conn.cursor()
#
#                 # 删除30天前的会话数据
#                 cursor.execute("""
#                     DELETE FROM user_sessions
#                     WHERE updated_at < datetime('now', '-{} days')
#                 """.format(days))
#
#                 deleted_sessions = cursor.rowcount
#
#                 cursor.execute("""
#                     DELETE FROM contract_chunks
#                     WHERE created_at < datetime('now', '-{} days')
#                 """.format(days))
#
#                 deleted_chunks = cursor.rowcount
#
#                 cursor.execute("""
#                     DELETE FROM review_context
#                     WHERE created_at < datetime('now', '-{} days')
#                 """.format(days))
#
#                 deleted_contexts = cursor.rowcount
#
#                 conn.commit()
#
#                 total_deleted = deleted_sessions + deleted_chunks + deleted_contexts
#                 logger.info(f"清理旧数据完成，共删除{total_deleted}条记录")
#                 return total_deleted
#
#         except Exception as e:
#             logger.error(f"清理旧数据失败: {e}")
#             return 0
#
