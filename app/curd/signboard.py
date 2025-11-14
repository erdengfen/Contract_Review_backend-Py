from datetime import datetime

from sqlalchemy import func

from app.models.review import ReviewTask, ReviewResult
from app.models.contract import ContractFile

from app.models.user import User
from sqlalchemy.orm import Session as DBSession
from typing import Optional, List


# 获取合同审阅概览
async def get_review_task_overview(db: DBSession) -> dict:
    """获取合同审阅概览"""
    total_tasks = db.query(ReviewTask).all()
    total_tasks_count = len(total_tasks)
    all_users=[vak.user_id for vak in total_tasks]
    unique_departments = set(db.query(User.department).filter(User.id.in_(all_users)).all())
    department_count = len(unique_departments)
    unique_users = set(all_users)
    user_count = len(unique_users)
    teacher_count = db.query(User).filter(User.role == 2).count()
    file_id=[vak.file_id for vak in total_tasks]
    total_reviewed_amount = db.query(ContractFile).filter(ContractFile.id.in_(file_id)).all()
    total_reviewed_amount = sum([float(vak.amount) for vak in total_reviewed_amount])

    return {
        "reviewed_contracts": int(total_tasks_count),
        "service_departments": int(department_count),
        "users_count": int(user_count),
        "served_faculty_students": int(teacher_count),
        "total_reviewed_amount": float(total_reviewed_amount),
    }


async def get_review_result(db: DBSession) -> dict:
    """
    获取合同审阅结果
    :param db:
    :return:
    """
    revisions_count = db.query(ReviewResult).count()
    accepted_count = db.query(ReviewResult).filter(ReviewResult.is_accepted == 1).count()
    error_count = revisions_count - accepted_count
    return {
        "risk_points_revised": revisions_count,
        "accepted_count": accepted_count,
        "error_points_revised": error_count,
    }

async def get_contract_types(db: DBSession) -> dict:
    """
    获取合同类型统计（总数量，使用单位，使用人数，服务类合同，货物类合同，基建类合同）
    :param db:
    :return:
    """
    total_count = db.query(ContractFile).count()
    user_ids=[vak.user_id for vak in db.query(ContractFile).all()]
    unique_contractors = set(db.query(User.department).filter(User.id.in_(user_ids)).all())

    return {
        "reviewed_contracts": int(total_count),
        "using_units": int(len(unique_contractors)),
        "users_count": int(len(set(user_ids))),
    }


async  def get_contract_count(db: DBSession, contract_type_id: int) -> dict:
    """
    获取合同类型统计（服务类合同，货物类合同，基建类合同）
    :param db:
    :param contract_type_id: 合同类型id
    :return:
    """
    contract_count = db.query(ContractFile).filter(ContractFile.contract_type_id == contract_type_id).count()

    return {
        "contract_count": contract_count,
    }


# 获取合同审阅趋势（总数量，服务类合同，货物类合同，基建类合同，分天，周，月，年）
async def get_review_trend(
        db: DBSession,
        time_granularity: str = 'day',
        contract_type_ids: List[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
) -> dict:
    """
    获取合同审阅趋势
    :param db: 数据库会话
    :param time_granularity: 时间粒度，可选值：'day', 'week', 'month', 'year'
    :param contract_type_ids: 合同类型ID列表，如果为None则获取所有类型
    :param start_time: 开始时间，如果为None则不限制
    :param end_time: 结束时间，如果为None则不限制
    :return: 包含各类合同数量和趋势的字典
    """
    if time_granularity == 'day':
        date_format = func.date_format(ReviewTask.created_at, "%Y-%m-%d")
    elif time_granularity == 'week':
        date_format = func.date_format(ReviewTask.created_at, "%Y-%u")
    elif time_granularity == 'month':
        date_format = func.date_format(ReviewTask.created_at, "%Y-%m")
    elif time_granularity == 'year':
        date_format = func.date_format(ReviewTask.created_at, "%Y")
    else:
        date_format = func.date_format(ReviewTask.created_at, "%Y-%m-%d")

    total_trend_query = db.query(
        date_format.label('time_period'),
        func.count(ReviewTask.id).label('total_count')
    )

    if start_time:
        total_trend_query = total_trend_query.filter(ReviewTask.created_at >= start_time)
    if end_time:
        total_trend_query = total_trend_query.filter(ReviewTask.created_at <= end_time)

    if contract_type_ids:
        total_trend_query = total_trend_query.join(
            ContractFile, ReviewTask.file_id == ContractFile.id
        ).filter(
            ContractFile.contract_type_id.in_(contract_type_ids)
        )

    total_trend_query = total_trend_query.group_by(date_format).order_by(date_format)

    total_trend = {}
    for item in total_trend_query.all():
        total_trend[item.time_period] = item.total_count

    trends = {
        "total": total_trend
    }

    if contract_type_ids:
        for type_id in contract_type_ids:
            type_trend_query = db.query(
                date_format.label('time_period'),
                func.count(ReviewTask.id).label('count')
            ).join(
                ContractFile, ReviewTask.file_id == ContractFile.id
            ).filter(
                ContractFile.contract_type_id == type_id
            )

            if start_time:
                type_trend_query = type_trend_query.filter(ReviewTask.created_at >= start_time)
            if end_time:
                type_trend_query = type_trend_query.filter(ReviewTask.created_at <= end_time)

            type_trend_query = type_trend_query.group_by(date_format).order_by(date_format)

            type_trend = {}
            for item in type_trend_query.all():
                type_trend[item.time_period] = item.count

            trends[f"type_{type_id}"] = type_trend

    total_counts = {}

    total_query = db.query(ReviewTask)
    if start_time:
        total_query = total_query.filter(ReviewTask.created_at >= start_time)
    if end_time:
        total_query = total_query.filter(ReviewTask.created_at <= end_time)

    if contract_type_ids:
        total_counts["total"] = total_query.join(
            ContractFile, ReviewTask.file_id == ContractFile.id
        ).filter(
            ContractFile.contract_type_id.in_(contract_type_ids)
        ).count()
    else:
        total_counts["total"] = total_query.count()

    if contract_type_ids:
        for type_id in contract_type_ids:
            type_query = db.query(ReviewTask).join(
                ContractFile, ReviewTask.file_id == ContractFile.id
            ).filter(
                ContractFile.contract_type_id == type_id
            )

            if start_time:
                type_query = type_query.filter(ReviewTask.created_at >= start_time)
            if end_time:
                type_query = type_query.filter(ReviewTask.created_at <= end_time)

            total_counts[f"type_{type_id}"] = type_query.count()

    return {
        "time_granularity": time_granularity,
        "total_counts": total_counts,
        "trends": trends
    }