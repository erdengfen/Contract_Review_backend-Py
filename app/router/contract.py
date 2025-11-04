"""
@Project ：Contract_Review_backend-Py 
@File    ：contract.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/22 14:45 
"""
import os
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
from openai import AsyncClient
from app.utils.document_parsing import docx2md, mk_pdf2docx
from app.curd.model_configs import get_default_model_by_type

router = APIRouter(tags=["合同管理"])
"""
文件上传 下载相关接口
"""


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
        model_config = await get_default_model_by_type(db, model_type="chat")

        async_client = AsyncClient(
            api_key=model_config.api_key,
            base_url=model_config.api_endpoint
        )
        if file.filename.split('.')[-1].lower() == "pdf":
            contract_content = docx2md(mk_pdf2docx(save_path, file.filename.replace('.pdf', '.docx')),                                       None)
        else:
            contract_content = docx2md(save_path, None)

        messages = [
            {
                "role": "system",
                "content": "你是一个合同类型识别助手, 能识别合同类型及甲乙方名称和金额。"
            },
            {
                "role": "user",
                "content": f"""
                请你根据文档内容识别合同类型，以及甲乙方的名称
                文档内容：{contract_content[:1000]}
                返回格式如下:
                甲方：{{甲方名称}}
                乙方：{{乙方名称}}
                金额：{{金额}}
                """
            }
        ]

        response = await async_client.chat.completions.create(
            model=model_config.model_name,
            stream=False,
            messages=messages,
            temperature=model_config.temperature,
            max_tokens=model_config.max_tokens,
            top_p=model_config.top_p,
            frequency_penalty=model_config.frequency_penalty,
            presence_penalty=model_config.presence_penalty
        )
        # 解析合同类型
        contract_type = response.choices[0].message.content
        party_a = contract_type.split("甲方：")[1].split("\n")[0].strip() if "甲方：" in contract_type else ""
        party_b = contract_type.split("乙方：")[1].strip() if "乙方：" in contract_type else ""
        amount = contract_type.split("金额：")[1].strip() if "金额：" in contract_type else ""
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


