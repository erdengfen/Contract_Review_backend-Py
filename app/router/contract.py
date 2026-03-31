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
from app.schemas.contract_file import UploadResponse, TransformContractRequest
from fastapi.responses import FileResponse
from app.utils.document_parsing import docx2md, mk_pdf2docx, extract_text_from_pdf, docx2text, doc2docx
from prompts.llm_prompt_vars import (
    CONTRACT_INFO_EXTRACTION_SYSTEM_PROMPT,
    build_contract_info_extraction_user_prompt,
)

router = APIRouter(tags=["合同管理"])
"""
文件上传 下载相关接口
"""


# def parse_contract_info(raw_output) -> dict:
#     pattern = r"```json\n(.*?)\n?```"
#     model_output=""
#     match = re.search(pattern, raw_output, re.DOTALL)
#     if match:
#         model_output = match.group(1)
#         print(model_output)
#
#     try:
#         data = json.loads(model_output)
#         party_a = data.get("party_a", "")
#         party_b = data.get("party_b", "")
#         amount = data.get("amount", "").replace("元", "")
#         def clean(val):
#             if not isinstance(val, str):
#                 return ""
#             if "{未识别}" in val or len(val) > 300:
#                 return ""
#             return val.strip()
#
#         return {
#             "party_a": clean(party_a),
#             "party_b": clean(party_b),
#             "amount": clean(amount)
#         }
#
#     except Exception as e:
#         return {"party_a": "", "party_b": "", "amount": ""}

def parse_contract_info(raw_output: str) -> dict:
    raw_output = raw_output.strip()

    # 尝试直接解析 JSON
    try:
        data = json.loads(raw_output)
    except Exception:
        # 如果不能解析，再尝试提取大括号中的内容
        try:
            json_text = re.search(r"\{[\s\S]*\}", raw_output).group(0)
            data = json.loads(json_text)
        except Exception:
            return {"party_a": "", "party_b": "", "amount": ""}

    def clean(val):
        if not isinstance(val, str):
            return ""
        if "{未识别}" in val or len(val) > 300:
            return ""
        return val.strip()

    return {
        "party_a": clean(data.get("party_a", "")),
        "party_b": clean(data.get("party_b", "")),
        "amount": clean(data.get("amount", "").replace("元", "")),
    }

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
            contract_content = extract_text_from_pdf(save_path)
        elif file.filename.split('.')[-1].lower() == "doc":
            output_path = save_path.replace(".doc", ".docx")
            doc2docx(input_path=save_path, output_path=output_path)
            contract_content = docx2text(output_path)
        else:
            # contract_content = docx2md(save_path, None)
            contract_content = docx2text(save_path)

        contract_type =  await llm_client.ainvoke(
            [
                SystemMessage(content=CONTRACT_INFO_EXTRACTION_SYSTEM_PROMPT),
                HumanMessage(
                    content=build_contract_info_extraction_user_prompt(contract_content)
                ),
            ]
        )
        contract_type = parse_contract_info(contract_type.content)

        party_a = contract_type["party_a"]
        party_b = contract_type["party_b"]
        amount = float(contract_type["amount"]) if contract_type["amount"] else 0.0
        print(party_a, party_b, amount)
        # 保存合同内容到文件
        base_name = os.path.splitext(file.filename)[0]
        new_filename = base_name + '.txt'
        contract_content_path = os.path.join(settings.OSS_BUCKET_DIR, new_filename)
        with open(contract_content_path, "w", encoding="utf-8") as f:
            f.write(contract_content)

        upload_result =await CRUDContract.create_contract_file(
            db=db,
            type="parsed",
            user_id=current_user.id,
            file_name=file.filename,
            file_type=file.filename.split('.')[-1].lower(),
            # contract_content=contract_content,
            contract_content_path=contract_content_path,
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



@router.post("/save_file", response_model=GenericResponse, summary="保存合同文件")
async def save_contract_file(
    current_user=Depends(optional_get_current_user),
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
):
    """保存合同文件"""

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

        upload_result = await CRUDContract.create_contract_file(
            db=db,
            type="uploaded",
            user_id=current_user.id,
            file_name=file.filename,
            file_type=file.filename.split('.')[-1].lower(),
            contract_content_path="",
            save_path=save_path,
            party_a="",
            party_b="",
            amount=0.0,
        )
        return GenericResponse(code=200, msg="上传成功", data=upload_result)

    except Exception as e:
        return GenericResponse(code=500, msg=f"文件上传失败: {str(e)}")
