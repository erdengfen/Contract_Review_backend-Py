"""
@Project ：Contract_Review_backend-Py 
@File    ：review_task.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/23 10:12 
"""
from datetime import datetime
from typing import Optional, List, Type
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import desc

from app.models.review import ReviewTask, ReviewResult
from app.schemas.review_task import ReviewTaskCreateRequest


class CRUDReviewTask:
    """审阅任务CRUD操作"""

    @staticmethod
    def create_review_task(
        db: DBSession,
        user_id: int,
        request: ReviewTaskCreateRequest
    ) -> ReviewTask:
        """创建审阅任务"""
        review_task = ReviewTask(
            contract_id=request.contract_id,
            session_id=request.session_id,
            user_id=user_id,
            stance=request.stance,
            intensity=request.intensity,
            description=request.description,
            status="pending"
        )
        db.add(review_task)
        db.commit()
        db.refresh(review_task)
        return review_task

    @staticmethod
    async def get_review_task(db: DBSession, session_id: int) -> Optional[ReviewTask]:
        """根据会话ID获取审阅任务"""
        return db.query(ReviewTask).filter(ReviewTask.session_id == session_id).first()






    # ------------------
    # @staticmethod
    # def get_review_task(db: DBSession, task_id: int) -> Optional[ReviewTask]:
    #     """根据任务ID获取审阅任务"""
    #     return db.query(ReviewTask).filter(ReviewTask.id == task_id).first()

    @staticmethod
    def get_review_user_task(db: DBSession, user_id: int,task_id: int) -> Optional[ReviewTask]:
        """根据用户ID获取用户发起的审阅任务"""
        return db.query(ReviewTask).filter(
            ReviewTask.user_id == user_id,
            ReviewTask.id == task_id
        ).first()

    @staticmethod
    def get_user_review_tasks(
        db: DBSession, 
        user_id: int, 
        skip: int = 0, 
        limit: int = 100
    ) -> list[Type[ReviewTask]]:
        """获取用户的审阅任务列表"""
        return  db.query(ReviewTask).filter(
            ReviewTask.user_id == user_id,
        ).order_by(
            desc(
                ReviewTask.created_at
            )
        ).offset(
            skip
        ).limit(
            limit
        ).all()
    @staticmethod
    def update_task_status(
        db: DBSession, 
        task_id: int, 
        status: str
    ) -> Optional[ReviewTask]:
        """更新任务状态"""
        task = db.query(ReviewTask).filter(ReviewTask.id == task_id).first()
        if task:
            task.status = status
            if status == "completed":
                task.completed_at = datetime.now()
            db.commit()
            db.refresh(task)
        return task



class CRUDReviewResult:
    """审查结果CRUD操作"""

    @staticmethod
    def create_review_result(
            db: DBSession,
            session_id: int,
            task_id: int,
            index: int,
            original_content: str,
            risk_analysis: str,
            risk_level: str,
            suggested_content: str,
    )-> ReviewResult:
        """创建审查结果"""
        review_result = ReviewResult(
            session_id=session_id,
            task_id=task_id,
            index=index,
            original_content=original_content,
            risk_analysis=risk_analysis,
            risk_level=risk_level,
            suggested_content=suggested_content,
        )
        db.add(review_result)
        db.commit()
        db.refresh(review_result)
        return review_result

    @staticmethod
    async def get_review_result(db: DBSession, task_id: int) -> Optional[ReviewResult]:
        """根据任务ID获取审查结果"""
        return db.query(ReviewResult).filter(ReviewResult.task_id == task_id).order_by(ReviewResult.index).all()

    # -----------------------
    # @staticmethod
    # def get_review_result(db: DBSession, result_id: int):
    #     """根据结果ID获取审查结果"""
    #     return db.query(ReviewResult).filter(ReviewResult.id == result_id).first()
    # @staticmethod
    # def get_review_task_results(db: DBSession, task_id: int) :
    #     """根据任务ID获取审查结果列表"""
    #     return db.query(ReviewResult).filter(
    #         ReviewResult.task_id == task_id).order_by(
    #         ReviewResult.index).all()
