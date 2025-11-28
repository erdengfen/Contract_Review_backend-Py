"""
合同比对任务 CRUD
"""
import json
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session as DBSession

from app.models import ComparisonTask


class CRUDComparisonTask:
    @staticmethod
    async def get_by_session(db: DBSession, session_id: int) -> Optional[ComparisonTask]:
        return (
            db.query(ComparisonTask)
            .filter(ComparisonTask.session_id == session_id)
            .first()
        )

    @staticmethod
    async def get_by_id(db: DBSession, task_id: int) -> Optional[ComparisonTask]:
        return db.query(ComparisonTask).filter(ComparisonTask.id == task_id).first()

    @staticmethod
    async def create_task(
        db: DBSession,
        *,
        session_id: int,
        user_id: int,
        standard_file_id: int,
        comparison_file_id: int,
    ) -> ComparisonTask:
        task = ComparisonTask(
            session_id=session_id,
            user_id=user_id,
            standard_file_id=standard_file_id,
            comparison_file_id=comparison_file_id,
            status="pending",
            diff_summary=None,
            diff_result=None,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    async def update_task_files(
        db: DBSession,
        task: ComparisonTask,
        *,
        standard_file_id: int,
        comparison_file_id: int,
    ) -> ComparisonTask:
        task.standard_file_id = standard_file_id
        task.comparison_file_id = comparison_file_id
        task.status = "pending"
        task.diff_summary = None
        task.diff_result = None
        task.completed_at = None
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    async def save_diff_result(
        db: DBSession,
        task: ComparisonTask,
        diff_summary: dict,
        diff_result: list,
    ) -> ComparisonTask:
        task.diff_summary = json.dumps(diff_summary, ensure_ascii=False)
        task.diff_result = json.dumps(diff_result, ensure_ascii=False)
        task.status = "completed"
        task.completed_at = datetime.now()
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    async def delete_by_session(db: DBSession, session_id: int) -> None:
        db.query(ComparisonTask).filter(
            ComparisonTask.session_id == session_id
        ).delete()
        db.commit()

