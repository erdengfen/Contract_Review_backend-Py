"""
@Project ：Contract_Review_backend-Py 
@File    ：cas_auth.py
@IDE     ：PyCharm 
@Author  ：cyanyumu
@Date    ：2025/10/28 
"""
from datetime import timedelta

import asyncio
import os

from fastapi import APIRouter, Header, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse, Response

from cas import CASClient

from app.config.config import settings
from app.core.dependencies import get_db
from sqlalchemy.orm import Session as DBSession
from app.curd.user import get_user_by_username, create_user
from app.middlewares.auth import create_access_token, jwt_config


router = APIRouter(tags=["CAS认证"])


async def delete_file_after_delay(file_path, delay_seconds):
    await asyncio.sleep(delay_seconds)
    if os.path.exists(file_path):
        os.remove(file_path)


def _build_service_url(request: Request) -> str:
    # 优先使用请求头中的 Host，避免 0.0.0.0
    scheme = request.url.scheme or "http"
    host = request.headers.get("host")
    if not host:
        host = f"{settings.server.host}:{settings.server.port}"
    return f"{scheme}://{host}/cas_callback"


def _build_frontend_redirect_url(request: Request, token: str) -> str:
    # 回跳到根路径并带上 token；若有前端地址，可在此处替换
    scheme = request.url.scheme or "http"
    host = request.headers.get("host")
    if not host:
        host = f"{settings.server.host}:{settings.server.port}"
    return f"{scheme}://{host}/?token={token}"


def _get_cas_client(service_url: str) -> CASClient:
    return CASClient(
        server_url="https://ids.cqupt.edu.cn/authserver/login",
        service_url=service_url,
        version=3,
    )


@router.get("/login/")
async def login(request: Request):
    service_url = _build_service_url(request)
    cas_client = _get_cas_client(service_url)
    return RedirectResponse(url=cas_client.get_login_url())


@router.get("/logout/")
async def logout(token: str = Header(None)):
    if token:
        response = Response(content="Successful Logout")
        response.delete_cookie(key="token")
        return response
    else:
        raise HTTPException(status_code=401, detail="Token not provided")


@router.get("/cas_callback")
async def cas_callback(request: Request, db: DBSession = Depends(get_db)):
    ticket = request.query_params.get('ticket')
    if not ticket:
        raise HTTPException(status_code=499, detail="Ticket not provided")

    service_url = _build_service_url(request)
    cas_client = _get_cas_client(service_url)

    try:
        user, attributes, pgtiou = cas_client.verify_ticket(ticket)
        user_name = attributes.get("userName") or user
        edu_person_type = attributes.get("eduPersonType")
        org_name = attributes.get("dwmc")
        gender = attributes.get("gender")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"CAS verification failed: {e}")

    # 查找或创建用户
    db_user = await get_user_by_username(db, user_name)
    if not db_user:
        # CAS 用户首次登录时创建账号，设置占位密码
        db_user = await create_user(db, user_name, password_hash="cas_login")

    # 生成访问令牌（与现有 JWT 逻辑一致）
    access_token_expires = timedelta(minutes=jwt_config.access_token_expire_minutes)
    access_token = await create_access_token(
        data={
            "sub": db_user.username,
            "user_id": db_user.id,
            "eduPersonType": edu_person_type,
            "dwmc": org_name,
            "gender": gender,
        },
        expires_delta=access_token_expires,
    )

    url = _build_frontend_redirect_url(request, access_token)
    return RedirectResponse(url=url)


