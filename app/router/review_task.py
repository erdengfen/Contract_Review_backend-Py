"""
@Project ：Contract_Review_backend-Py 
@File    ：review.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/22 14:13 
"""
from fastapi import APIRouter, Depends

from app.middlewares.auth import optional_get_current_user
from app.schemas.base import GenericResponse

router = APIRouter(tags=["合同审阅"])
"""
合同问答，审阅相关接口
"""



@router.post("/ask", response_model=GenericResponse[ChatResponse],summary="")
async def ask_question(
        current_user=Depends(optional_get_current_user),
        request: ChatRequest = Body(...)
):
    """合同问答"""
    pass

@router.post("/modified", response_model=GenericResponse[ChatResponse],summary="合同修改")
async def modified_contract(
        current_user=Depends(optional_get_current_user),
        request: ChatRequest = Body(...)
):
    """合同修改"""
    pass



@router.post("/report", response_model=GenericResponse[ChatResponse],summary="合同审阅报告")
async def report_contract(
        current_user=Depends(optional_get_current_user),
        request: ChatRequest = Body(...)
):
    """合同审阅报告"""
    pass
