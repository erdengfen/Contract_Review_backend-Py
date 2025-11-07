from fastapi import APIRouter, Depends
from fastapi import  Query
from typing import List, Optional
from datetime import date
from sqlalchemy.orm import Session
from app.curd.signboard import get_review_trend, get_review_result, get_review_task_overview
from app.core.dependencies import get_db
from app.schemas.signboard import (OverviewResponse, RevisionsResponse,
                                   ContractTypesResponse, TrendItem, DepartmentUsageItem)

from app.schemas.base import GenericResponse
router = APIRouter()





@router.get("/statistics_overview", response_model=GenericResponse[OverviewResponse],
            summary="获取合同审阅概览 (合同审阅数量（个），服务业务部门（个），使用人数（人），服务师生数量（个），累计审阅金额（元）)")
async def get_overview(
        db: Session = Depends(get_db),
):
    """
    获取合同审阅概览（审阅合同数量（个），服务业务部门（个），使用人数（人），服务师生数量（个），累计审阅金额（元））
    :return:
    """
    overview = await get_review_task_overview(db)
    return GenericResponse(code=200, msg="获取合同审阅概览成功", data=overview)

@router.get("/statistics_revisions", response_model=GenericResponse[RevisionsResponse],
            summary="获取修订风险点（个），修订错误点（个）")
async def get_revisions(
        db: Session = Depends(get_db),):
    """
    获取修订风险点（个），修订错误点（个）
    :return:
    """
    revisions = await get_review_result(db)
    return GenericResponse(code=200, msg="获取修订风险点（个），修订错误点（个）成功", data=revisions)

@router.get("/statistics_contract-types", response_model=GenericResponse[ContractTypesResponse],
            summary="获取合同类型统计（总数量，使用单位，使用人数）")
async def get_contract_types(
        db: Session = Depends(get_db),
):
    """
        获取合同类型统计（总数量，使用单位，使用人数）
    :return:
    """

    contract_types = await get_contract_types(db)
    return GenericResponse(code=200, msg="获取合同类型统计（总数量，使用单位，使用人数）成功", data=contract_types)


@router.post("/get_contract_count", response_model=GenericResponse[dict],
             summary="获取合同类型统计（服务类合同，货物类合同，基建类合同）")
async def get_contract_count(
        db: Session = Depends(get_db),
        contract_type_id: int = Query(..., description="合同类型id")
):
    """
    获取合同类型统计（服务类合同，货物类合同，基建类合同）
    :param db:
    :param contract_type_id: 合同类型id
    :return:
    """

    contract_count = await get_contract_count(db, contract_type_id)
    return GenericResponse(code=200, msg="获取合同类型统计（服务类合同，货物类合同，基建类合同）成功", data=contract_count)

@router.get("/trends_contracts", response_model=GenericResponse[List[TrendItem]],
            summary="获取合同审阅趋势（总数量，服务类合同，货物类合同，基建类合同，分天，周，月，年）")
async def get_contract_trends(
        db: Session = Depends(get_db),
        period: str = Query(..., regex="^(day|week|month|year)$"),
    contract_type_ids: Optional[List[int]] = Query(None, description="合同类型id列表"),

    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    """
    获取合同审阅趋势（总数量，服务类合同，货物类合同，基建类合同，分天，周，月，年）
    :param period:
    :param start_date:
    :param end_date:
    :return:
    """

    trends = await get_review_trend(db, period,contract_type_ids, start_date, end_date)
    return GenericResponse(code=200, msg="获取合同审阅趋势（总数量，服务类合同，货物类合同，基建类合同，分天，周，月，年）成功", data=trends)



@router.get("/departments_usage", response_model=GenericResponse[List[DepartmentUsageItem]],
            summary="获取业务单位使用情况（合同审阅，合同校验，合同比对，合计）按照部门进行")
async def get_department_usage(
        db: Session = Depends(get_db),
):
    """
        获取业务单位使用情况（合同审阅，合同校验，合同比对，合计）按照部门进行
    :return:
    """
    pass
