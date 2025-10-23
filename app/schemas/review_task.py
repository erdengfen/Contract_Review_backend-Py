"""
@Project ：Contract_Review_backend-Py 
@File    ：review_task.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/23 10:12 
"""


class ChatRequest(BaseModel):
    """合同问答请求"""
    contract_id: str = Field(..., description="合同ID")
    question: str = Field(..., description="用户问题")
