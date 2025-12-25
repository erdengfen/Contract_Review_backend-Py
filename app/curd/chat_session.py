"""
@Project ：Contract_Review_backend-Py 
@File    ：session_chat.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/23 11:43 
"""

from datetime import datetime
from sqlalchemy.orm import Session as DBSession, aliased
from app.models import Session, Message, ContractFile, ComparisonTask
from typing import Optional, List, Any, Coroutine
from app.curd.comparison_task import CRUDComparisonTask
from app.schemas.session import ReviewSessionResponse, CompareSessionResponse

class CRUDSession:

    @staticmethod
    async def create_session(db: DBSession, user_id: int, title: str, file_id: Optional[int] = None,session_type:[str]='default'):
        """创建新会话"""
        new_session = Session(
            title=title,
            user_id=user_id,
            session_type=session_type,
            file_id=file_id,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        return new_session

    @staticmethod
    async def get_user_sessions(db: DBSession,
                                user_id: int,
                                session_type:str,
                                skip: int = 0,
                                limit: int = 10,
                                ) -> list[ReviewSessionResponse] | list[CompareSessionResponse] | list[Any]:
        """分页获取用户的会话历史"""
        if session_type == 'review':
            query = (
                db.query(
                    Session.id,
                    Session.title,
                    Session.session_type,
                    Session.file_id,
                    Session.created_at,
                    ContractFile.party_a,
                    ContractFile.party_b,
                    ContractFile.is_accepted,
                )
                .outerjoin(
                    ContractFile,
                    Session.file_id == ContractFile.id
                )
                .filter(
                    Session.user_id == user_id,
                    Session.session_type == session_type
                )
                .order_by(Session.created_at.desc())
                .offset(skip)
                .limit(limit)
            )

            rows = query.all()

            return [
                ReviewSessionResponse(
                    id=row.id,
                    title=row.title,
                    session_type=row.session_type,
                    file_id=row.file_id,
                    created_at=row.created_at,
                    party_a=row.party_a,
                    party_b=row.party_b,
                    is_accepted=bool(row.is_accepted) if row.is_accepted is not None else False,
                )
                for row in rows
            ]
        elif session_type == 'compare':
            ContractFile1 = aliased(ContractFile)
            ContractFile2 = aliased(ContractFile)

            query = (
                db.query(
                    Session.id,
                    Session.title,
                    Session.session_type,
                    Session.created_at,

                    ContractFile1.id.label("file_id"),
                    ContractFile1.party_a.label("party_a"),
                    ContractFile1.party_b.label("party_b"),
                    ContractFile1.is_accepted.label("is_accepted"),

                    ContractFile2.id.label("file_id_2"),
                    ContractFile2.party_a.label("party_a_2"),
                    ContractFile2.party_b.label("party_b_2"),
                    ContractFile2.is_accepted.label("is_accepted_2"),
                )
                .outerjoin(
                    ComparisonTask,
                    ComparisonTask.session_id == Session.id
                )
                .outerjoin(
                    ContractFile1,
                    ContractFile1.id == ComparisonTask.standard_file_id
                )
                .outerjoin(
                    ContractFile2,
                    ContractFile2.id == ComparisonTask.comparison_file_id
                )
                .filter(
                    Session.user_id == user_id,
                    Session.session_type == session_type
                )
                .order_by(Session.created_at.desc())
                .offset(skip)
                .limit(limit)
            )

            rows = query.all()

            return [
                CompareSessionResponse(
                    id=row.id,
                    title=row.title,
                    session_type=row.session_type,
                    created_at=row.created_at,

                    file_id=row.file_id,
                    party_a=row.party_a,
                    party_b=row.party_b,
                    is_accepted=bool(row.is_accepted) if row.is_accepted is not None else False,

                    file_id_2=row.file_id_2,
                    party_a_2=row.party_a_2,
                    party_b_2=row.party_b_2,
                    is_accepted_2=bool(row.is_accepted_2) if row.is_accepted_2 is not None else False,
                )
                for row in rows
            ]
        else:
            return []

    @staticmethod
    async def count_user_sessions(db: DBSession, user_id: int, session_type: Optional[str] = None) -> int:
        """统计用户的会话总数"""
        query = db.query(Session).filter(Session.user_id == user_id)
        if session_type:
            query = query.filter(Session.session_type == session_type)
        return query.count()

    @staticmethod
    async def delete_session(db: DBSession, session_id: int, user_id: int):
        """删除用户指定会话"""
        session_obj = db.query(Session).filter(
            Session.id == session_id,
            Session.user_id == user_id
        ).first()
        if not session_obj:
            return False
        if session_obj.session_type == 'chat':
            # 需要删除关联的消息记录
            pass
        elif session_obj.session_type == 'review':
            # 需要删除关联的审阅记录
            pass
        elif session_obj.session_type == 'compare':
            await CRUDComparisonTask.delete_by_session(db, session_obj.id)

        try:
            db.delete(session_obj)
            db.commit()
            return True
        except Exception as e:
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
        except Exception as e:
            print(f"更新会话标题失败: {e}")
            db.rollback()
            return None

    @staticmethod
    async def get_session(db: DBSession, session_id: int):
        """获取指定会话"""
        return (db.query(Session).filter(
                Session.id == session_id,).first())

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

