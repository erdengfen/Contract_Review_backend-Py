"""
@Project ：Contract_Review_backend-Py 
@File    ：review_task.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/23 10:12 
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import desc

from app.models.review import ReviewTask, ReviewResult, RiskItem
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
    def get_review_task(db: DBSession, task_id: int) -> Optional[ReviewTask]:
        """根据任务ID获取审阅任务"""
        return db.query(ReviewTask).filter(ReviewTask.id == task_id).first()

    @staticmethod
    def get_user_review_tasks(
        db: DBSession, 
        user_id: int, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[ReviewTask]:
        """获取用户的审阅任务列表"""
        return db.query(ReviewTask)\
            .filter(ReviewTask.user_id == user_id)\
            .order_by(desc(ReviewTask.created_at))\
            .offset(skip)\
            .limit(limit)\
            .all()

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

    @staticmethod
    def create_review_result(
        db: DBSession,
        task_id: int,
        overall_risk: str,
        summary: str,
        suggestion: str
    ) -> ReviewResult:
        """创建审阅结果"""
        review_result = ReviewResult(
            task_id=task_id,
            overall_risk=overall_risk,
            summary=summary,
            suggestion=suggestion
        )
        db.add(review_result)
        db.commit()
        db.refresh(review_result)
        return review_result

    @staticmethod
    def create_risk_item(
        db: DBSession,
        result_id: int,
        clause_text: str,
        risk_type: str,
        risk_level: str,
        suggestion: str
    ) -> RiskItem:
        """创建风险项"""
        risk_item = RiskItem(
            result_id=result_id,
            clause_text=clause_text,
            risk_type=risk_type,
            risk_level=risk_level,
            suggestion=suggestion
        )
        db.add(risk_item)
        db.commit()
        db.refresh(risk_item)
        return risk_item

    @staticmethod
    def get_review_result(db: DBSession, task_id: int) -> Optional[ReviewResult]:
        """获取审阅结果"""
        return db.query(ReviewResult).filter(ReviewResult.task_id == task_id).first()

    @staticmethod
    def get_risk_items(db: DBSession, result_id: int) -> List[RiskItem]:
        """获取风险项列表"""
        return db.query(RiskItem).filter(RiskItem.result_id == result_id).all()

    @staticmethod
    def delete_review_task(db: DBSession, task_id: int) -> bool:
        """删除审阅任务及其相关数据"""
        try:
            # 删除风险项
            db.query(RiskItem).filter(RiskItem.result_id.in_(
                db.query(ReviewResult.id).filter(ReviewResult.task_id == task_id)
            )).delete(synchronize_session=False)
            
            # 删除审阅结果
            db.query(ReviewResult).filter(ReviewResult.task_id == task_id).delete()
            
            # 删除审阅任务
            db.query(ReviewTask).filter(ReviewTask.id == task_id).delete()
            
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            return False
