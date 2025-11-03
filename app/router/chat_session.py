"""
@Project ：Contract_Review_backend-Py 
@File    ：session.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/23 10:31 
"""

from fastapi import APIRouter, Depends, Body, Query
from app.core.dependencies import get_db
from app.curd.chat_session import CRUDSession, CRUDMessage
from app.curd.contract_file import CRUDContract
from app.middlewares.auth import optional_get_current_user
from sqlalchemy.orm import Session as DBSession
from app.schemas.session_chat import SessionResponse, CreateSessionRequest, UpdateSessionTitleRequest, \
    SessionListResponse, MessageResponse, MessageCreateRequest
from app.schemas.base import GenericResponse


router = APIRouter(tags=["会话管理"])

@router.post("/create", response_model=GenericResponse[SessionResponse], summary="创建会话")
async def create_session(
    request: CreateSessionRequest,
    db: DBSession = Depends(get_db),
    current_user=Depends(optional_get_current_user)
):
    """创建新的会话（支持关联合同文件或不关联）"""

    if not current_user:
        return GenericResponse(code=401, msg="用户未登录")

    # 验证关联合同文件
    if request.contract_id:
        contract = await CRUDContract.get_contract_file(db=db, file_id=request.contract_id)
        if not contract:
            return GenericResponse(code=404, msg="关联的合同文件不存在")

    try:
        session_obj =await CRUDSession.create_session(
            db=db,
            user_id=current_user.id,
            title=request.title,
            session_type=request.session_type,
            contract_id=request.contract_id
        )

        response_data = SessionResponse(
            session_id=session_obj.id,
            title=session_obj.title,
            session_type=session_obj.session_type,
            contract_id=session_obj.contract_id,
            created_at=session_obj.created_at.isoformat()
        )
        return GenericResponse(code=200, msg="会话创建成功", data=response_data)

    except Exception as e:
        db.rollback()
        return GenericResponse(code=500, msg=f"创建会话失败: {str(e)}")



@router.get("/list", response_model=GenericResponse[SessionListResponse], summary="分页获取会话历史列表")
async def list_user_sessions(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=100, description="每页数量"),
    db: DBSession = Depends(get_db),
    current_user=Depends(optional_get_current_user)
):
    """分页获取当前用户的会话历史记录"""
    if not current_user:
        return GenericResponse(code=401, msg="用户未登录")

    skip = (page - 1) * size
    sessions =await CRUDSession.get_user_sessions(db=db, user_id=current_user.id, skip=skip, limit=size)
    total =await  CRUDSession.count_user_sessions(db=db, user_id=current_user.id)

    session_list = [
        SessionResponse(
            session_id=s.id,
            title=s.title,
            session_type=s.session_type,
            contract_id=s.contract_id,
            created_at=s.created_at.isoformat(),
        )
        for s in sessions
    ]

    return GenericResponse(
        code=200,
        msg="获取成功",
        data=SessionListResponse(total=total, sessions=session_list)
    )


@router.delete("/{session_id}", response_model=GenericResponse, summary="删除指定会话记录")
async def delete_user_session(
    session_id: int,
    db: DBSession = Depends(get_db),
    current_user=Depends(optional_get_current_user)
):
    """删除指定历史会话记录"""
    if not current_user:
        return GenericResponse(code=401, msg="用户未登录")

    success =await  CRUDSession.delete_session(db=db, session_id=session_id, user_id=current_user.id)
    if not success:
        return GenericResponse(code=404, msg="会话不存在或删除失败")

    return GenericResponse(code=200, msg="会话删除成功")


@router.post("/{session_id}/title", response_model=GenericResponse[SessionResponse], summary="修改会话标题")
async def update_session_title(
    session_id: int,
    request: UpdateSessionTitleRequest = Body(...),
    db: DBSession = Depends(get_db),
    current_user=Depends(optional_get_current_user)
):
    """修改指定会话的标题"""
    if not current_user:
        return GenericResponse(code=401, msg="用户未登录")

    session_obj =await  CRUDSession.update_session_title(
        db=db,
        session_id=session_id,
        user_id=current_user.id,
        new_title=request.new_title
    )
    if not session_obj:
        return GenericResponse(code=404, msg="会话不存在或无权限修改")

    return GenericResponse(
        code=200,
        msg="标题修改成功",
        data=SessionResponse(
            session_id=session_obj.id,
            title=session_obj.title,
            session_type=session_obj.session_type,
            contract_id=session_obj.contract_id,
            created_at=session_obj.created_at.isoformat(),
        )
    )


@router.post("/message_send", response_model=GenericResponse[MessageResponse], summary="发送消息")
async def send_message(
    request: MessageCreateRequest,
    db: DBSession = Depends(get_db),
    current_user=Depends(optional_get_current_user)
):
    """发送消息"""
    if not current_user:
        return GenericResponse(code=401, msg="用户未登录")

    msg =await  CRUDMessage.create_message(
        db=db,
        session_id=request.session_id,
        role=request.role,
        content=request.content,
        parent_id=request.parent_id
    )
    return GenericResponse(code=200, msg="消息发送成功", data=MessageResponse.model_validate(msg))


@router.get("/message_list", response_model=GenericResponse[list[MessageResponse]], summary="获取会话消息列表")
async def list_messages(
    session_id: int = Query(..., description="会话ID"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: DBSession = Depends(get_db),
    current_user=Depends(optional_get_current_user)
):
    """分页获取会话消息"""
    if not current_user:
        return GenericResponse(code=401, msg="用户未登录")

    skip = (page - 1) * size
    messages =await  CRUDMessage.get_messages(db=db, session_id=session_id, skip=skip, limit=size)
    return GenericResponse(code=200, msg="查询成功", data=messages)

