"""
@Project ：Contract_Review_backend-Py 
@File    ：session.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/11/4 10:38 
"""
from typing import List

from fastapi import APIRouter, Depends

from app.core.dependencies import get_db
from app.curd.chat_session import CRUDSession
from app.curd.contract_file import CRUDContract
from app.curd.review_task import CRUDReviewTask, CRUDReviewResult
from app.middlewares.auth import optional_get_current_user

from sqlalchemy.orm import Session as DBSession

from app.models import Message
from app.schemas.base import GenericResponse
from app.schemas.session import SessionResponse, SessionListResponse, ListSessionRequest, CreateSessionRequest, \
    UpdateSessionTitleRequest, DeleteSessionRequest, SessionHistoryDetailRequest

router = APIRouter(tags=["会话管理"])
"""
会话管理相关接口
"""



@router.post("/create_session",
             response_model=GenericResponse[SessionResponse],
             summary="创建会话")
async def create_session(
    request: CreateSessionRequest,
    db: DBSession = Depends(get_db),
    current_user=Depends(optional_get_current_user)
):
    """创建新的会话（支持关联合同文件或不关联）"""
    if not current_user:
        return GenericResponse(code=401, msg="用户未登录")

    # 验证关联合同文件
    if request.file_id:
        contract = await CRUDContract.get_contract_file(db=db, file_id=request.file_id)
        if not contract:
            return GenericResponse(code=404, msg="关联的合同文件不存在")

    try:
        session_obj =await CRUDSession.create_session(
            db=db,
            user_id=current_user.id,
            title=request.title,
            session_type=request.session_type,
            file_id=request.file_id
        )

        response_data = SessionResponse(
            session_id=session_obj.id,
            title=session_obj.title,
            session_type=session_obj.session_type,
            file_id=session_obj.file_id,
            created_at=session_obj.created_at.isoformat()
        )
        return GenericResponse(code=200, msg="会话创建成功", data=response_data)

    except Exception as e:
        db.rollback()
        return GenericResponse(code=500, msg=f"创建会话失败: {str(e)}")


@router.post("/list_sessions",
             response_model=GenericResponse[SessionListResponse],
             summary="获取用户会话列表（根据会话类型）")
async def list_sessions(
        request: ListSessionRequest,
        db: DBSession = Depends(get_db),
        current_user=Depends(optional_get_current_user)
):
        """获取用户会话列表（根据会话类型）"""
        if not current_user:
            return GenericResponse(code=401, msg="用户未登录")
        if request.page < 1 or request.page_size <1:
            return GenericResponse(
                code=400,
                msg="页码和每页数量必须大于等于1"
            )
        skip=(request.page - 1) * request.page_size
        sessions=await  CRUDSession.get_user_sessions(
            db=db,
            user_id=current_user.id,
            skip=skip,
            limit=request.page_size,
            session_type=request.session_type
        )
        total = await  CRUDSession.count_user_sessions(db=db,
                                                       user_id=current_user.id,
                                                       session_type=request.session_type)
        return GenericResponse(
            code=200,
            msg="会话列表获取成功",
            data=SessionListResponse(
                total=total,
                sessions=sessions
            )
        )

@router.post("/update_session_title",
             response_model=GenericResponse[SessionResponse],
             summary="修改会话标题")
async def update_session_title(
    request: UpdateSessionTitleRequest,
    db: DBSession = Depends(get_db),
    current_user=Depends(optional_get_current_user)
):
    """修改指定会话的标题"""
    if not current_user:
        return GenericResponse(code=401, msg="用户未登录")

    session_obj =await  CRUDSession.update_session_title(
        db=db,
        session_id=request.session_id,
        user_id=current_user.id,
        new_title=request.new_title
    )
    if not session_obj:
        return GenericResponse(code=404, msg="会话不存在或无权限修改")

    return GenericResponse(
        code=200,
        msg="标题修改成功",
        data=SessionResponse(
            session_id=request.session_id,
            title=session_obj.title,
            session_type=session_obj.session_type,
            file_id=session_obj.file_id,
            created_at=session_obj.created_at.isoformat(),
        )
    )

@router.post("/delete_session",
             response_model=GenericResponse[bool],
             summary="删除会话")
async def delete_session(
    request: DeleteSessionRequest,
    db: DBSession = Depends(get_db),
    current_user=Depends(optional_get_current_user)
):
    """删除指定会话"""
    if not current_user:
        return GenericResponse(code=401, msg="用户未登录")

    success = await CRUDSession.delete_session(
        db=db,
        session_id=request.session_id,
        user_id=current_user.id
    )
    if not success:
        return GenericResponse(code=404, msg="会话不存在或无权限删除")

    return GenericResponse(
        code=200,
        msg="会话删除成功",
        data=True
    )



@router.post("/session_history_detail",
             summary="获取会话历史记录")
async def session_history_detail(
        request: SessionHistoryDetailRequest,
        db: DBSession = Depends(get_db),
        current_user=Depends(optional_get_current_user)
):
        """获取会话历史记录"""
        if not current_user:
            return GenericResponse(code=401, msg="用户未登录")
        session = await CRUDSession.get_session(db, request.session_id)
        if not session:
            return GenericResponse(code=404, msg="会话不存在")
        if session.session_type == "chat":
            raw_messages = db.query(Message).filter(Message.session_id == request.session_id).order_by(Message.created_at).all()
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
            return GenericResponse(
                code=200,
                msg="会话历史记录获取成功",
                data=formatted_messages
            )
        elif session.session_type == "review":
            file_id=session.file_id
            # 获取审批任务相关信息
            review_task = await CRUDReviewTask.get_review_task(db, file_id)
            if not review_task:
                return GenericResponse(code=404, msg="合同审阅任务不存在")
            # 获取审批任务结果详情
            review_results = await CRUDReviewResult.get_review_result(db, review_task.id)
            return GenericResponse(
                code=200,
                msg="合同审阅结果获取成功",
                data=[val.dict() for val in review_results]
            )
        else:
            return GenericResponse(code=400, msg="会话类型错误")
