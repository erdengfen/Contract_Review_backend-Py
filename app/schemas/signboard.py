from typing import List, Optional

from pydantic import BaseModel,Field

class OverviewResponse(BaseModel):
    reviewed_contracts: Optional[int]=Field(default=None,description="审阅合同数量（个）")
    service_departments: int=Field(default=None,description="服务业务部门（个）")
    users_count: int=Field(default=None,description="使用人数（人）")
    served_faculty_students: int=Field(default=None,description="服务师生数量（个）")
    total_reviewed_amount: float=Field(default=None,description="累计审阅金额（元）")

class RevisionsResponse(BaseModel):
    risk_points_revised: int=Field(default=None,description="修订风险点（个）")
    error_points_revised: int=Field(default=None,description="修订错误点（个）")

class ContractTypesResponse(BaseModel):
    reviewed_contracts: int=Field(default=None,description="合同类型总数量（个）")
    using_units: List[str]=Field(default=None,description="使用单位（可改为数量 int，此处保留列表更灵活）")
    users_count: int=Field(default=None,description="使用人数（人）")
    service_contracts: int=Field(default=None,description="服务类合同（个）")
    goods_contracts: int=Field(default=None,description="货物类合同（个）")
    infrastructure_contracts: int=Field(default=None,description="基建类合同（个）")

class TrendItem(BaseModel):
    date: Optional[str]=Field(default=None,description="数据日期（格式如 \"2025-10\" 或 \"2025-W42\"）")
    total: int=Field(default=None,description="合同类型总数量（个）")
    service: int=Field(default=None,description="服务类合同（个）")
    goods: int=Field(default=None,description="货物类合同（个）")
    infrastructure: int=Field(default=None,description="基建类合同（个）")

class DepartmentUsageItem(BaseModel):
    department_name: str=Field(default=None,description="部门名称")
    contract_review: int=Field(default=None,description="合同审阅（个）")
    contract_verification: int=Field(default=None,description="合同校验（个）")
    contract_comparison: int=Field(default=None,description="合同比对（个）")
    total: int=Field(default=None,description="合同类型总数量（个）")


class TrendsContractsRequest(BaseModel):
        period: str=Field(default=None,description="时间周期（day,week,month,year）")
        contract_type_ids: Optional[List[int]]=Field(default=None,description="合同类型id列表")
        start_date: Optional[str]=Field(default=None,description="开始日期（格式如 \"2025-10-01\"）")
        end_date: Optional[str]=Field(default=None,description="结束日期（格式如 \"2025-10-31\"）")
