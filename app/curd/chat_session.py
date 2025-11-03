"""
@Project ：Contract_Review_backend-Py 
@File    ：session_chat.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/23 11:43 
"""

from datetime import datetime
from sqlalchemy.orm import Session as DBSession
from app.models import Session, Message
from typing import Optional

class CRUDSession:

    @staticmethod
    async def create_session(db: DBSession, user_id: int, title: str, contract_id: Optional[int] = None,session_type:[str]='default'):
        """创建新会话"""
        new_session = Session(
            title=title,
            user_id=user_id,
            session_type=session_type,
            contract_id=contract_id,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        return new_session

    @staticmethod
    async def get_user_sessions(db: DBSession, user_id: int, skip: int = 0, limit: int = 10):
        """分页获取用户的会话历史"""
        return (
            db.query(Session)
            .filter(Session.user_id == user_id)
            .order_by(Session.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    async def count_user_sessions(db: DBSession, user_id: int) -> int:
        """统计用户的会话总数"""
        return db.query(Session).filter(Session.user_id == user_id).count()

    @staticmethod
    async def delete_session(db: DBSession, session_id: int, user_id: int):
        """删除用户指定会话"""
        session_obj = db.query(Session).filter(
            Session.id == session_id,
            Session.user_id == user_id
        ).first()
        if not session_obj:
            return False
        try:
            db.delete(session_obj)
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False

    @staticmethod
    async def update_session_title(db: DBSession, session_id: int, user_id: int, new_title: str) :
        """更新会话标题"""
        session_obj = db.query(Session).filter(
            Session.id == session_id,
            Session.user_id == user_id
        ).first()
        if not session_obj:
            return None
        try:
            session_obj.title = new_title
            session_obj.updated_at = datetime.now()
            db.commit()
            db.refresh(session_obj)
            return session_obj
        except Exception:
            db.rollback()
            return None

    @staticmethod
    async def get_session(db: DBSession, session_id: int):
        """获取指定会话"""
        return (
            db.query(Session)
            .filter(
                Session.id == session_id,
            )
            .first()
        )

class CRUDMessage:
    @staticmethod
    async def create_message(db: DBSession, session_id: int, role: str, content: str, parent_id: int = None):
        """创建新消息"""
        message_index = (
            db.query(Message)
            .filter(Message.session_id == session_id)
            .count() + 1
        )

        msg = Message(
            session_id=session_id,
            role=role,
            content=content,
            parent_id=parent_id,
            message_index=message_index,
            created_at=datetime.now()
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)
        return msg

    @staticmethod
    async def get_messages(db: DBSession, session_id: int, skip: int = 0, limit: int = 20):
        """分页获取会话消息"""
        return (
            db.query(Message)
            .filter(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )

