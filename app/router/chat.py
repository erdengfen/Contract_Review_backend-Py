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
from app.curd.chat_session import CRUDSession
from app.models.session_message import Session, Message

from app.curd.chat import get_or_create_chat_session, create_message,chat_stream_generator, get_message_history_as_dicts
from app.curd.model_configs import get_default_model_by_type
from app.schemas.chat import ChatRequest

router = APIRouter(tags=["合同聊天"])



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

