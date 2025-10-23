"""
@Project ：Contract_Review_backend-Py 
@File    ：session.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/23 10:31 
"""

from fastapi import APIRouter, Depends, Body


from app.core.dependencies import get_db
from app.middlewares.auth import optional_get_current_user
from app.models import Session, Message
from sqlalchemy.orm import Session as DBSession
from datetime import datetime
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.base import GenericResponse


router = APIRouter(prefix="/chat", tags=["会话管理"])
@router.post("/create_session", response_model=GenericResponse[ChatResponse], summary="创建会话")
async def create_session(
    current_user=Depends(optional_get_current_user),
    db: DBSession = Depends(get_db),
    request: ChatRequest = Body(...)
):
    """创建对话会话（支持带文件/不带文件两种模式）"""
    if not current_user:
        return GenericResponse(code=401, msg="用户未登录")

    try:
        # 自动命名
        session_title = request.title or f"新建会话_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 创建会话
        new_session = Session(
            contract_id=request.contract_id,
            user_id=current_user.id,
            title=session_title,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db.add(new_session)
        db.commit()
        db.refresh(new_session)

        # 如果用户传了初始消息，创建首条 Message
        if request.message:
            new_message = Message(
                session_id=new_session.id,
                role="user",
                content=request.message,
                created_at=datetime.now()
            )
            db.add(new_message)
            db.commit()

        return GenericResponse(
            code=200,
            msg="会话创建成功",
            data=ChatResponse(
                session_id=new_session.id,
                title=new_session.title,
                contract_id=new_session.contract_id,
                created_at=new_session.created_at.isoformat()
            )
        )

    except Exception as e:
        db.rollback()
        return GenericResponse(code=500, msg=f"创建会话失败: {str(e)}")