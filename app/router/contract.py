"""
@Project ：Contract_Review_backend-Py 
@File    ：contract.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/22 14:45 
"""
import json
import os
import re
import shutil

from langchain_core.messages import SystemMessage, HumanMessage
from sqlalchemy.orm import Session

from app.config.config import settings
from app.core import llm
from app.core.dependencies import get_db
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends

from app.curd.contract_file import CRUDContract, CRUDContractType
from app.middlewares.auth import optional_get_current_user

from  app.schemas.base import GenericResponse
from app.schemas.contract_file import UploadResponse
from fastapi.responses import FileResponse

from app.utils.document_parsing import docx2md, mk_pdf2docx

router = APIRouter(tags=["合同管理"])
"""
文件上传 下载相关接口
"""


def parse_contract_info(raw_output) -> dict:
    pattern = r"```json\n(.*?)\n?```"
    model_output=""
    match = re.search(pattern, raw_output, re.DOTALL)
    if match:
        model_output = match.group(1)
        # print(model_output)
    data = json.loads(model_output)
    try:
        party_a = data.get("party_a", "")
        party_b = data.get("party_b", "")
        amount = data.get("amount", "").replace("元", "")
        def clean(val):
            if not isinstance(val, str):
                return ""
            if "{未识别}" in val or len(val) > 300:
                return ""
            return val.strip()

        return {
            "party_a": clean(party_a),
            "party_b": clean(party_b),
            "amount": clean(amount)
        }

    except (json.JSONDecodeError, TypeError, AttributeError):
        return {"party_a": "", "party_b": "", "amount": ""}
@router.post("/upload", response_model=GenericResponse[UploadResponse], summary="上传合同文件")
async def upload_contract_file(
    current_user=Depends(optional_get_current_user),
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
):
    """上传合同文件"""
    if not current_user:
        return GenericResponse(code=401, msg="用户未登录")

    if not file.filename:
        return GenericResponse(code=400, msg="文件名不能为空")

    try:
        save_dir = os.path.join(settings.UPLOAD_DIR, str(current_user.id))
        os.makedirs(save_dir, exist_ok=True)

        save_path = os.path.join(save_dir, file.filename)
        with open(save_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        # 识别合同类型
        llm_client =  llm.init_llm()
        if file.filename.split('.')[-1].lower() == "pdf":
            contract_content = docx2md(mk_pdf2docx(save_path, file.filename.replace('.pdf', '.docx')),                                       None)
        else:
            contract_content = docx2md(save_path, None)
        contract_type =  llm_client.invoke(
            [
                SystemMessage(content="""
                你是一个专业的合同信息提取引擎，请严格遵守以下规则：

                1. **仅处理合同类文档**。如果输入内容不是合同（如论文、通知、模板等），请返回：
                ```json
                {
                    "party_a": "{未识别}", 
                    "party_b": "{未识别}", 
                    "amount": "{未识别}"
                }
                ```
                2. **必须以纯 JSON 格式输出，且仅包含以下三个字段**：
                   - "party_a": 甲方全称（字符串）
                   - "party_b": 乙方全称（字符串）
                   - "amount": 合同金额及单位（字符串，如 "50000元"）

                3. **字段规则**：
                   - 若无法识别某字段，值为 "{未识别}"
                   - 不要包含任何额外字段、注释、markdown、换行或说明文字
                   - 输出必须是合法 JSON，可被 Python `json.loads()` 解析

                4. **禁止行为**：
                   - 禁止输出非 JSON 内容（如“好的，结果如下：”）
                   - 禁止推测、虚构信息
                   - 禁止使用中文引号、单引号（必须双引号）

                5. **正确示例**：
                ```json
                {
                    "party_a": "华为技术有限公司", 
                    "party_b": "中国移动通信集团", 
                    "amount": "12500000元"
                }
                ```
                """),
                HumanMessage(content=f"请提取以下文档中的合同信息：\n\n{contract_content[:1200]}")
            ]
        )
        # 解析合同类型
        contract_type = parse_contract_info(contract_type.content)

        party_a = contract_type["party_a"]
        party_b = contract_type["party_b"]
        amount = float(contract_type["amount"]) if contract_type["amount"] else 0.0
        print(party_a, party_b, amount)
        upload_result =await CRUDContract.create_contract_file(
            db=db,
            user_id=current_user.id,
            file_name=file.filename,
            file_type=file.filename.split('.')[-1].lower(),
            contract_content=contract_content,
            save_path=save_path,
            party_a=party_a,
            party_b=party_b,
            amount=amount,
        )
        return GenericResponse(code=200, msg="上传成功", data=upload_result)
    except Exception as e:
        return GenericResponse(code=500, msg=f"文件上传失败: {str(e)}")

@router.post("/set_contract_type", response_model=GenericResponse, summary="设置合同类型及其审查立场")
async def set_contract_type(
    file_id: int,
    contract_type_id: int,
    review_position: int,
    db: Session = Depends(get_db),
):
    """设置合同类型及其审查立场"""
    success =await CRUDContract.set_contract_type(db=db, file_id=file_id, contract_type_id=contract_type_id, review_position=review_position)
    if not success:
        return GenericResponse(code=400, msg="合同类型不存在")
    return GenericResponse(code=200, msg="合同类型及其审查立场设置成功")



@router.get("/download/{file_id}", summary="下载文件")
async def download_contract_file(file_id: int, db: Session = Depends(get_db)):
    """下载合同文件"""
    file_record =await CRUDContract.get_contract_file(db=db, file_id=file_id)
    if not file_record:
        raise HTTPException(status_code=404, detail="文件不存在")

    if not os.path.exists(file_record.file_path):
        raise HTTPException(status_code=404, detail="文件已丢失")

    return FileResponse(
        path=file_record.file_path,
        filename=os.path.basename(file_record.file_path),
        media_type="application/octet-stream"
    )




@router.delete("/{file_id}", response_model=GenericResponse, summary="删除合同文件")
async def delete_contract_file(file_id: int, db: Session = Depends(get_db)):
    """删除合同文件"""
    success =await CRUDContract.delete_contract_file(db=db, file_id=file_id)
    if not success:
        return GenericResponse(code=404, msg="文件不存在或删除失败")
    return GenericResponse(code=200, msg="文件删除成功")


