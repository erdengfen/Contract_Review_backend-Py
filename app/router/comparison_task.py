"""
合同比对任务路由
"""
import json
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from app.core.dependencies import get_db
from app.curd.chat_session import CRUDSession
from app.curd.comparison_task import CRUDComparisonTask
from app.curd.contract_file import CRUDContract
from app.middlewares.auth import optional_get_current_user
from app.models.session_message import SessionTypeEnum
from app.schemas.base import GenericResponse
from app.schemas.comparison_task import (
    ComparisonTaskCreateRequest,
    ComparisonTaskResponse,
    FileInfo,
)
from app.services.document_comparison import diff_docs

router = APIRouter(tags=["合同比对"])


def _build_file_info(contract) -> FileInfo:
    return FileInfo(
        file_id=contract.id,
        title=contract.title,
        file_type=contract.file_type,
        file_path=contract.file_path,
        download_url=f"/api/contract/download/{contract.id}",
    )


async def _ensure_compare_session(
    *,
    db: DBSession,
    current_user,
    session_id: Optional[int],
    title: str,
) -> int:
    """校验或创建比对会话。"""
    if session_id:
        session_obj = await CRUDSession.get_session(db, session_id)
        if not session_obj or session_obj.user_id != current_user.id:
            raise ValueError("会话不存在或无权限")
        if session_obj.session_type != SessionTypeEnum.COMPARE.value:
            raise ValueError("会话类型必须为compare")
        return session_obj.id

    session_obj = await CRUDSession.create_session(
        db=db,
        user_id=current_user.id,
        title=title,
        session_type=SessionTypeEnum.COMPARE.value,
        file_id=None,
    )
    return session_obj.id


@router.post(
    "/start",
    response_model=GenericResponse[ComparisonTaskResponse],
    summary="启动合同比对任务",
)
async def start_comparison_task(
    request: ComparisonTaskCreateRequest,
    db: DBSession = Depends(get_db),
    current_user=Depends(optional_get_current_user),
):
    if not current_user:
        return GenericResponse(code=401, msg="用户未登录")

    std_file = await CRUDContract.get_contract_file(
        db=db, file_id=request.standard_file_id
    )
    cmp_file = await CRUDContract.get_contract_file(
        db=db, file_id=request.comparison_file_id
    )
    if not std_file or not cmp_file:
        return GenericResponse(code=404, msg="文档不存在")
    if std_file.file_type.lower() != "docx" or cmp_file.file_type.lower() != "docx":
        return GenericResponse(code=400, msg="目前仅支持 docx 文件比对")

    try:
        session_title = (
            request.title or f"{std_file.title} VS {cmp_file.title}".strip()
        )
        session_id = await _ensure_compare_session(
            db=db,
            current_user=current_user,
            session_id=request.session_id,
            title=session_title,
        )
    except ValueError as exc:
        return GenericResponse(code=400, msg=str(exc))

    task = await CRUDComparisonTask.get_by_session(db, session_id)
    if task:
        task = await CRUDComparisonTask.update_task_files(
            db,
            task,
            standard_file_id=std_file.id,
            comparison_file_id=cmp_file.id,
        )
    else:
        task = await CRUDComparisonTask.create_task(
            db,
            session_id=session_id,
            user_id=current_user.id,
            standard_file_id=std_file.id,
            comparison_file_id=cmp_file.id,
        )

    try:
        diff_data = diff_docs(std_file.file_path, cmp_file.file_path)
    except FileNotFoundError as exc:
        return GenericResponse(code=404, msg=str(exc))
    except Exception as exc:
        return GenericResponse(code=500, msg=f"比对失败: {exc}")

    task = await CRUDComparisonTask.save_diff_result(
        db,
        task,
        diff_summary=diff_data["summary"],
        diff_result=diff_data["diffs"],
    )

    response = ComparisonTaskResponse(
        task_id=task.id,
        session_id=session_id,
        diff_summary=diff_data["summary"],
        diffs=diff_data["diffs"],
        standard_file=_build_file_info(std_file),
        comparison_file=_build_file_info(cmp_file),
    )
    return GenericResponse(code=200, msg="比对完成", data=response)

