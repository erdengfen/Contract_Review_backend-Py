"""
@Project ：Contract_Review_backend-Py 
@File    ：chat.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/11/2 14:21 
"""
import json

from langchain_core.messages import HumanMessage, AIMessage
from openai import AsyncClient
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional

from app.core.llm import stream_chat_model
from app.models.session_message import Session as DBSession, Message
from app.models.session_message import Message as DBMessage
from app.schemas.model_configs import ModelConfigSchema


def get_or_create_chat_session(db: Session, contract_id: int, session_id: Optional[int] = None, user_id: int = None) -> DBSession:
    """
    获取或创建合同对应的聊天会话
    :param db: 数据库会话
    :param contract_id: 合同ID
    :param user_id: 用户ID
    :return: 聊天会话对象
    """
    session = db.query(DBSession).filter(
        and_(
            DBSession.contract_id == contract_id,
            DBSession.user_id == user_id,
            DBSession.id == session_id,
            DBSession.session_type == "chat"
        )
    ).first()

    if not session:
        title = f"合同 #{contract_id} 的对话"
        session = DBSession(
            contract_id=contract_id,
            user_id=user_id,
            title=title,
            session_type="chat"
        )
        db.add(session)
        db.commit()
        db.refresh(session)
    return session

# 创建新消息
def create_message(
    db: Session,
    session_id: int,
    role: str,
    content: str,
    parent_id: Optional[int] = None,
    message_index: Optional[int] = None
) -> DBMessage:
    # 自动计算 message_index（如果未提供）
    if message_index is None:
        last_msg = db.query(DBMessage).filter(
            DBMessage.session_id == session_id
        ).order_by(DBMessage.message_index.desc()).first()
        message_index = (last_msg.message_index or 0) + 1 if last_msg else 1

    message = DBMessage(
        session_id=session_id,
        role=role,
        content=content,
        parent_id=parent_id,
        message_index=message_index
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message

from app.models.session_message import Session

def get_message_history_as_dicts(db: Session, session_id: int) -> List[dict]:
    messages = db.query(Message).filter(
        Message.session_id == session_id
    ).order_by(Message.message_index).all()

    history = []
    for msg in messages:
        role = "user" if msg.role == "user" else "assistant"
        history.append({
            "role": role,
            "content": msg.content
        })
    return history
async def chat_stream_generator(
    async_client: AsyncClient,
    messages: list,
    model_config: ModelConfigSchema,
    db: Session,
    session_id: int
):
    """
        生成器：流式输出 AI 回复，并在结束后保存完整内容
    """
    # 查询会话信息，获取contract_id等额外信息
    session = db.query(Session).filter(Session.id == session_id).first()
    contract_id = session.contract_id if session else None
    user_id = session.user_id if session else None
    
    full_content = ""
    try:
        async for delta in stream_chat_model(async_client, messages, model_config):
            full_content += delta
            yield f"data: {json.dumps({
                'type': 'content',
                'session_id': session_id,
                'contract_id': contract_id,
                'user_id': user_id,
                'content': delta,
                'role': 'assistant'
            }, ensure_ascii=False)}\n\n"
        
        # 创建消息记录
        message = create_message(
            db=db,
            session_id=session_id,
            role="assistant",
            content=full_content
        )
        
        # 完成时返回更多信息
        yield f"data: {json.dumps({
            'type': 'done',
            'session_id': session_id,
            'contract_id': contract_id,
            'user_id': user_id,
            'message_id': message.id if message else None,
            'full_content': full_content
        }, ensure_ascii=False)}\n\n"

    except Exception as e:
        error_msg = f"AI 生成出错: {str(e)}"
        yield f"data: {json.dumps({
            'type': 'error',
            'session_id': session_id,
            'contract_id': contract_id,
            'user_id': user_id,
            'error': error_msg
        }, ensure_ascii=False)}\n\n"

        raise

def get_message_history(db: Session, session_id: int):
    """
    获取聊天会话的消息历史记录
    :param db: 数据库会话
    :param session_id: 会话ID
    :return: 包含 HumanMessage 和 AIMessage 的列表
    """
    messages = db.query(DBMessage).filter(
        DBMessage.session_id == session_id
    ).order_by(DBMessage.message_index).all()

    history = []
    for msg in messages:
        if msg.role == "user":
            history.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            history.append(AIMessage(content=msg.content))
    return history

def get_chat_history_by_contract(db: Session, session_id: int) -> List[DBSession]:
    """
    获取合同对应的所有聊天会话及消息（按 session 分组）
    :param db: 数据库会话
    :param session_id: 会话ID
    :return: 包含会话和消息的列表
    """
    session = db.query(DBSession).filter(
        and_(
            DBSession.id == session_id,
            DBSession.session_type == "chat"
        )
    ).first()

    if not session:
        return []

    # 为 session 加载其消息（按 message_index 排序）
    session.messages = db.query(DBMessage).filter(
        DBMessage.session_id == session.id
    ).order_by(DBMessage.message_index).all()

    return session


def get_session_by_id(db: Session, session_id: int) -> Optional[DBSession]:
    """
    根据会话ID获取会话
    :param db: 数据库会话
    :param session_id: 会话ID
    :return: 会话对象或None
    """
    return db.query(DBSession).filter(
        and_(
            DBSession.id == session_id,
            DBSession.session_type == "chat"
        )
    ).first()


def create_new_session(db: Session, contract_id: int, user_id: int, title: Optional[str] = None) -> DBSession:
    """
    创建新的聊天会话
    :param db: 数据库会话
    :param contract_id: 合同ID
    :param user_id: 用户ID
    :param title: 会话标题（可选）
    :return: 创建的会话对象
    """
    if not title:
        title = f"合同 #{contract_id} 的对话"
    
    session = DBSession(
        contract_id=contract_id,
        user_id=user_id,
        title=title,
        session_type="chat"
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def update_session_title(db: Session, session_id: int, title: str) -> Optional[DBSession]:
    """
    更新会话标题
    :param db: 数据库会话
    :param session_id: 会话ID
    :param title: 新标题
    :return: 更新后的会话对象或None
    """
    session = get_session_by_id(db, session_id)
    if session:
        session.title = title
        session.updated_at = datetime.now()
        db.commit()
        db.refresh(session)
    return session


def delete_session(db: Session, session_id: int) -> bool:
    """
    删除会话及其所有消息
    :param db: 数据库会话
    :param session_id: 会话ID
    :return: 是否删除成功
    """
    # 先删除所有相关消息
    db.query(DBMessage).filter(DBMessage.session_id == session_id).delete()
    
    # 再删除会话
    result = db.query(DBSession).filter(
        and_(
            DBSession.id == session_id,
            DBSession.session_type == "chat"
        )
    ).delete()
    
    db.commit()
    return result > 0


def delete_message(db: Session, message_id: int, session_id: int) -> bool:
    """
    删除特定消息
    :param db: 数据库会话
    :param message_id: 消息ID
    :param session_id: 会话ID（用于验证权限）
    :return: 是否删除成功
    """
    result = db.query(DBMessage).filter(
        and_(
            DBMessage.id == message_id,
            DBMessage.session_id == session_id
        )
    ).delete()
    
    db.commit()
    return result > 0


def get_user_sessions(db: Session, user_id: int) -> List[DBSession]:
    """
    获取用户的所有聊天会话
    :param db: 数据库会话
    :param user_id: 用户ID
    :return: 会话列表
    """
    sessions = db.query(DBSession).filter(
        and_(
            DBSession.user_id == user_id,
            DBSession.session_type == "chat"
        )
    ).order_by(DBSession.updated_at.desc()).all()
    
    # 为每个会话添加消息计数
    for session in sessions:
        session.message_count = db.query(DBMessage).filter(
            DBMessage.session_id == session.id
        ).count()
    
    return sessions


def get_session_messages(db: Session, session_id: int) -> List[DBMessage]:
    """
    获取特定会话的所有消息
    :param db: 数据库会话
    :param session_id: 会话ID
    :return: 消息列表
    """
    return db.query(DBMessage).filter(
        DBMessage.session_id == session_id
    ).order_by(DBMessage.message_index).all()