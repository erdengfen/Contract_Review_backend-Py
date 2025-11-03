"""
@Project ：Contract_Review_backend-Py 
@File    ：chat.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/11/2 14:09 
"""
import json
from typing import List

from fastapi import APIRouter, HTTPException, Depends
from langchain_core.messages import HumanMessage
from openai import AsyncClient
from sqlalchemy.orm import Session
from starlette.responses import StreamingResponse
from app.middlewares.auth import optional_get_current_user
from app.core.dependencies import get_db
from app.core.llm import  init_chat_model
from app.curd.chat_session import CRUDSession
from app.models.session_message import Session, Message
from app.schemas.session_chat import SessionListResponse
from app.schemas.chat import ChatSessionResponse

from app.curd.chat import get_or_create_chat_session, create_message, get_chat_history_by_contract, get_message_history, \
    chat_stream_generator, get_message_history_as_dicts
from app.curd.model_configs import get_default_model_by_type
from app.schemas.chat import ChatRequest, ChatSessionResponse, ChatMessageResponse, CreateSessionRequest, UpdateSessionTitleRequest

router = APIRouter(tags=["合同聊天"])






@router.post("/chat", summary="合同聊天接口（流式）")
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user=Depends(optional_get_current_user)
):
    contract=await CRUDSession.get_session(db, request.session_id)
    if not contract:
        raise HTTPException(status_code=404, detail="会话不存在")
    session = get_or_create_chat_session(
        db=db,
        contract_id=contract.contract_id,
        session_id=request.session_id,
        user_id=current_user.id if current_user else None
    )   

    # 2. 保存用户消息
    create_message(
        db=db,
        session_id=session.id,
        role="user",
        content=request.content,
        parent_id=request.parent_id
    )

    model_config = await get_default_model_by_type(db, model_type="chat") 

    async_client = AsyncClient(
        api_key=model_config.api_key,
        base_url=model_config.api_endpoint
    )

    history = get_message_history_as_dicts(db, session.id)  
    max_turns = getattr(session, 'max_context_length', 5) * 2  
    
    if len(history) > max_turns:
        history = history[-max_turns:]
    
    return StreamingResponse(
        chat_stream_generator(
            async_client=async_client,
            messages=history,
            model_config=model_config,
            db=db,
            session_id=session.id
        ),
        media_type="text/event-stream"
    )


@router.get("/get_chat_session/{session_id}", summary="获取特定会话的聊天记录")
async def get_session_chat_history(
    session_id: int,
    db: Session = Depends(get_db)
):
    # 使用非异步方法获取会话
    session = await CRUDSession.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    # 获取原始消息记录
    raw_messages = db.query(Message).filter(Message.session_id == session_id).order_by(Message.created_at).all()
    
    # 转换为符合ChatSessionResponse模型的消息格式
    formatted_messages = []
    for msg in raw_messages:
        formatted_messages.append({
            "id": msg.id,
            "session_id": msg.session_id,
            "role": msg.role,
            "content": msg.content,
            "parent_id": msg.parent_id,
            "message_index": msg.message_index,
            "created_at": msg.created_at
        })
    
    return ChatSessionResponse(
        session_id=session.id,
        title=session.title,
        messages=formatted_messages
    )


@router.get("/get_user_chat_session_list/{user_id}", summary="获取用户的所有聊天会话")
async def get_user_chat_sessions(
    user_id: int,
    page: int = 1,
    size: int = 100,
    db: Session = Depends(get_db)
):
    
    if page < 1:
        page = 1
    skip = (page - 1) * size
    
    # 使用同步方法获取用户会话列表
    # 注意：这里使用直接查询而不是调用可能是异步的CRUDSession方法
    sessions = db.query(Session).filter(
        Session.user_id == user_id
    ).order_by(Session.updated_at.desc()).offset(skip).limit(size).all()
    
    # 获取总数
    total = db.query(Session).filter(Session.user_id == user_id).count()
    
    # 构建会话列表，确保符合SessionResponse模型
    session_list = []
    for sess in sessions:
        # 构建符合SessionResponse模型的会话对象
        # 添加所有必需字段，确保created_at转换为字符串
        session_item = {
            "session_id": sess.id,
            "title": sess.title,
            "session_type": getattr(sess, "session_type", "normal"),  # 默认值为normal
            "contract_id": getattr(sess, "contract_id", None),
            "created_at": sess.created_at.isoformat() if sess.created_at else ""
        }
        session_list.append(session_item)
    
    # 按照SessionListResponse模型格式返回
    return SessionListResponse(
        total=total,
        sessions=session_list
    )


@router.post("/update_session_title/{session_id}", summary="更新会话标题")
async def update_session_title_endpoint(
    session_id: int,
    request: UpdateSessionTitleRequest,
    db: Session = Depends(get_db),
    current_user=Depends(optional_get_current_user)
):
    session = await CRUDSession.update_session_title(db, session_id, current_user.id, request.title)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {
        "session_id": session.id,
        "title": session.title,
        "updated_at": session.updated_at
    }


@router.post("/delete_chat_session/{session_id}", summary="删除聊天会话")
async def delete_chat_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(optional_get_current_user)
):
    success = await CRUDSession.delete_session(db, session_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"message": "会话删除成功"}
