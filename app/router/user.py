"""
@Project ：Contract_Review_backend-Py 
@File    ：user.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/22 09:52 
"""
from datetime import timedelta

from fastapi import Depends, APIRouter, HTTPException
from sqlalchemy.orm import Session
from starlette import status

from app.core.dependencies import get_db
from app.curd.user import authenticate_user
from app.middlewares.auth import get_valid_tokens, jwt_config, create_access_token, create_refresh_token, \
    optional_get_current_user
from app.models import User
from  app.schemas.base import GenericResponse
from app.curd import user as user_crud
from app.schemas.user import UserResponse, UserCreate, UserUpdate, LoginRequest, LoginResponse

router = APIRouter(tags=["用户管理"])


@router.post("/create", response_model=GenericResponse[UserResponse], summary="创建用户")
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """创建用户"""
    existing =await user_crud.get_user_by_username(db, user.username)
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")
    new_user =await user_crud.create_user(db, user.username, user.password)
    return GenericResponse(data=new_user)


@router.get("/{user_id}", response_model=GenericResponse[UserResponse], summary="根据ID查询用户")
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """根据ID查询用户"""
    db_user = await user_crud.get_user_by_id(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return GenericResponse(data=db_user)

# @router.get("/me", response_model=GenericResponse[UserResponse], summary="获取当前登录用户信息")
# async def get_current_user(
#         db: Session = Depends(get_db),
#     current_user = Depends(optional_get_current_user)):
#     """获取当前登录用户信息"""
#     if not current_user:
#         raise HTTPException(status_code=401, detail="未登录或令牌无效")
#
#     return GenericResponse(data=current_user)



@router.get("/all", response_model=GenericResponse[list[UserResponse]], summary="获取所有用户（仅活跃用户）")
async def get_all_users(db: Session = Depends(get_db)):
    """获取所有用户（仅活跃用户）"""
    users = await user_crud.get_all_users(db)
    return GenericResponse(data=users)


@router.put("/update/{user_id}", response_model=GenericResponse[UserResponse], summary="更新用户信息")
async def update_user(user_id: int, user: UserUpdate, db: Session = Depends(get_db)):
    """更新用户信息"""
    db_user = await user_crud.get_user_by_id(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="用户不存在")

    updated_user = await user_crud.update_user(
        db,
        user_id=user_id,
        username=user.username,
        password_hash=user.password
    )
    return GenericResponse(data=updated_user)


@router.post("/disable/{user_id}", response_model=GenericResponse[dict], summary="逻辑删除用户（禁用账号）")
async def disable_user(user_id: int, db: Session = Depends(get_db)):
    """逻辑删除用户"""
    db_user = await user_crud.get_user_by_id(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="用户不存在")

    status= await user_crud.delete_user(db, user_id)
    if not status:
        raise HTTPException(status_code=500, detail="删除用户失败")
    return GenericResponse(data={"message": f"用户 {db_user.username} 删除成功"})


@router.post("/login", response_model=GenericResponse[LoginResponse], summary="用户登录")
async def login_for_access_token(
        request: LoginRequest, db: Session = Depends(get_db)
):
    """
    用户登录
    :param request: 登录请求
    :param db: 数据库会话
    :return: 访问令牌和刷新令牌
    """
    user = await authenticate_user(db, request.identifier, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect identifier or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 检查 Redis 中是否存在有效的令牌
    valid_tokens = await get_valid_tokens(user.id)
    if valid_tokens:
        access_token, refresh_token = valid_tokens
    else:
        access_token_expires = timedelta(minutes=jwt_config.access_token_expire_minutes)
        refresh_token_expires = timedelta(days=jwt_config.refresh_token_expire_days)
        # 存储令牌到 Redis
        access_token = await create_access_token(
            data={"sub": user.username, "user_id": user.id}, expires_delta=access_token_expires
        )
        # 存储刷新令牌到 Redis
        refresh_token = await create_refresh_token(
            data={"sub": user.username, "user_id": user.id}, expires_delta=refresh_token_expires
        )

    return GenericResponse(code=200, msg="登录成功", data=LoginResponse(
        access_token=access_token,
        token_type="bearer",
        refresh_token=refresh_token
    ))
