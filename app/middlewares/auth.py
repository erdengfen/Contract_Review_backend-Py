"""
@Project ：Contract_Review_backend-Py 
@File    ：auth.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/22 16:26 
"""
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import WebSocket, Depends, HTTPException
from fastapi.security import HTTPBearer
from oauthlib.oauth2 import MissingTokenError
from jwt.exceptions import InvalidTokenError as JWTError, ExpiredSignatureError
import jwt
from datetime import datetime, timedelta
from app.schemas.user import TokenData
from app.curd.user import get_user_by_username
from app.config.config import settings
from app.core.dependencies import get_db
from sqlalchemy.orm import Session
from app.core.redis import RedisHandler


from app.schemas.base import BaseSchema

jwt_config=settings.jwt_config

default_exclude_paths = [
    "/openapi.json",
    "/docs",
    "/static/**",
    "/api/user/create",
    "/api/user/login",
    "/api/user/refresh",
    "/api/user/cas_login",
    "/api/user/cas_callback",
    "/api/contract/upload",
    "/login/",
    "/logout/",
    "/cas_callback"
]

auth_scheme = HTTPBearer()

redis_handler = RedisHandler()

async def acquire_login_lock(user_id: str, ttl: int = 5) -> bool:
    return redis_handler.set(
        f"login:lock:{user_id}",
        "1",
        ex=ttl
    )

async def release_login_lock(user_id: str):
    redis_handler.delete(f"login:lock:{user_id}")


async def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """
    创建访问令牌并存储到 Redis
    :param data: 包含用户信息的字典
    :param expires_delta: 令牌过期时间
    :return: 访问令牌
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=jwt_config.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, jwt_config.secret_key, algorithm=jwt_config.algorithm)

    # 存储 access_token 到 Redis，使用 user_id 作为键
    user_id = data.get("user_id")
    if user_id:
        ex = int(expire.timestamp() - datetime.utcnow().timestamp())
        redis_handler.set(f"access_token:{user_id}", encoded_jwt, ex=ex)

    return encoded_jwt


async def create_refresh_token(data: dict, expires_delta: timedelta | None = None):
    """
    创建刷新令牌并存储到 Redis
    :param data: 包含用户信息的字典
    :param expires_delta: 令牌过期时间
    :return: 刷新令牌
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=jwt_config.refresh_token_expire_days)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, jwt_config.refresh_secret_key, algorithm=jwt_config.algorithm)

    # 存储 refresh_token 到 Redis，使用 user_id 作为键
    user_id = data.get("user_id")
    if user_id:
        ex = int(expire.timestamp() - datetime.utcnow().timestamp())
        redis_handler.set(f"refresh_token:{user_id}", encoded_jwt, ex=ex)
    return encoded_jwt


async def verify_refresh_token(refresh_token: str):
    """
    验证刷新令牌并检查 Redis
    :param refresh_token: 刷新令牌
    :return: 令牌数据
    """
    try:
        payload = jwt.decode(refresh_token, jwt_config.refresh_secret_key, algorithms=[jwt_config.algorithm])

        user_id = payload.get("user_id")
        if user_id:
            stored_refresh_token = redis_handler.get(f"refresh_token:{user_id}")
            if stored_refresh_token:
                stored_refresh_token = stored_refresh_token

            if stored_refresh_token != refresh_token:
                error = BaseSchema(code=401, msg="Invalid refresh token", data=None)
                # raise HTTPException(status_code=401, detail=error.dict())
                return error
        return payload
    except JWTError as e:

        error = BaseSchema(code=401, msg="Invalid refresh token", data=None)
        # raise HTTPException(status_code=401, detail=error.dict())
        return error

async def revoke_user_tokens(user_id: str):
    """
    使用户的 access_token 和 refresh_token 失效
    """
    redis_handler.delete(f"access_token:{user_id}")
    redis_handler.delete(f"refresh_token:{user_id}")


async def get_current_user(token: HTTPAuthorizationCredentials = Depends(auth_scheme), db: Session = Depends(get_db)):
    """
    获取当前用户并检查 Redis 中的 access_token
    :param token: 包含访问令牌的 HTTP 授权凭证
    :param db: 数据库会话
    :return: 当前用户信息
    """
    credentials_exception = HTTPException(
        status_code=401,
        detail=BaseSchema(code=401, msg="Could not validate credentials", data=None).dict(),
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token.credentials, jwt_config.secret_key, algorithms=[jwt_config.algorithm])

        username: str = payload.get("sub")
        user_id = payload.get("user_id")
        if username is None or user_id is None:
            # raise credentials_exception
            return BaseSchema(code=401, msg="Could not validate credentials", data=None)

        token_data = TokenData(username=username)

        # 检查 Redis 中的 access_token，使用 user_id 作为键
        stored_access_token = redis_handler.get(f"access_token:{user_id}")
        if stored_access_token:
            stored_access_token = stored_access_token

        if stored_access_token != token.credentials:
            # raise credentials_exception
            return BaseSchema(code=401, msg="access_token != token.credentials", data=None)
    except JWTError as e:

        # raise credentials_exception
        return BaseSchema(code=401, msg=f"JWT error: {e}", data=None)
    user =await get_user_by_username(db, token_data.username)
    if user is None:
        return BaseSchema(code=401, msg="user is None", data=None)
        # raise credentials_exception
    return user

def path_is_excluded(path: str, exclude_paths: list):
    for p in exclude_paths:
        # 支持 /static/** 模式
        if p.endswith("/**"):
            if path.startswith(p[:-3]):
                return True
        elif path == p:
            return True
    return False
async def verify_token(request: Request, exclude_paths: list = None):
    """
    验证令牌
    :param request: 请求对象
    :param exclude_paths: 不需要验证的路径列表
    :return:
    """
    if exclude_paths is None:
        exclude_paths = default_exclude_paths

    if path_is_excluded(request.url.path, exclude_paths):
        return
    try:
        credentials: HTTPAuthorizationCredentials = await auth_scheme(request)
        token = credentials.credentials

        payload = jwt.decode(token, jwt_config.secret_key, algorithms=[jwt_config.algorithm])
    except ExpiredSignatureError as e:

        error = BaseSchema(code=401, msg="Token has expired", data=None)
        return error
        # raise HTTPException(status_code=401, detail=error.dict())
    except MissingTokenError:

        error = BaseSchema(code=401, msg="Missing token", data=None)
        return error
        # raise HTTPException(status_code=401, detail=error.dict())
    except JWTError as e:

        error = BaseSchema(code=401, msg="Invalid token", data=None)
        return error
        # raise HTTPException(status_code=401, detail=error.dict())
    except Exception as e:

        if "403" in str(e) or "Not authenticated" in str(e):
            error = BaseSchema(code=403, msg="Not authenticated", data=None)
        elif "401" in str(e):
            error = BaseSchema(code=401, msg="Invalid token", data=None)
        elif "400" in str(e):
            error = BaseSchema(code=400, msg="Invalid token", data=None)
        else:
            error = BaseSchema(code=500, msg="Internal Server Error", data=None)
        return error
        # raise HTTPException(status_code=500, detail=error.dict())


async def optional_get_current_user(token: HTTPAuthorizationCredentials = Depends(auth_scheme),
                                    db: Session = Depends(get_db)):
    """
    可选地获取当前用户，如果没有有效令牌则返回None
    :param token: 包含访问令牌的HTTP授权凭证
    :param db: 数据库会话
    :return: 当前用户信息或None
    """
    try:
        payload = jwt.decode(token.credentials, jwt_config.secret_key, algorithms=[jwt_config.algorithm])

        username: str = payload.get("sub")
        user_id = payload.get("user_id")
        if username is None or user_id is None:
            return None

        # 检查Redis中的access_token
        stored_access_token = redis_handler.get(f"access_token:{user_id}")
        if stored_access_token:
            stored_access_token = stored_access_token

        if stored_access_token != token.credentials:
            return None

        user =await get_user_by_username(db, username)
        if user is None:
            return None

        return user
    except Exception as e:
        print(f"optional_get_current_user error: {e}")
        # 捕获所有异常，包括JWTError、KeyError等
        # 不记录具体错误，以避免日志过于冗长
        return None


async def get_valid_tokens(user_id: str):
    """
    获取 Redis 中有效的 access_token 和 refresh_token
    :param user_id: 用户 ID
    :return: 有效的 access_token 和 refresh_token，如果不存在则返回 None
    """
    access_token = redis_handler.get(f"access_token:{user_id}")
    refresh_token = redis_handler.get(f"refresh_token:{user_id}")

    if access_token and refresh_token:
        try:
            # 验证 access_token 是否有效
            jwt.decode(access_token, jwt_config.secret_key, algorithms=[jwt_config.algorithm])
            # 验证 refresh_token 是否有效
            jwt.decode(refresh_token, jwt_config.refresh_secret_key, algorithms=[jwt_config.algorithm])
            return access_token, refresh_token
        except JWTError:
            return None
    return None





async def get_current_user_websocket(
        websocket: WebSocket,
        db: Session = Depends(get_db)
):
    """
    获取当前用户（用于WebSocket连接）
    :param websocket: WebSocket连接
    :param db: 数据库会话
    :return: 当前用户信息
    """
    # 从查询参数或头部获取令牌
    token = None

    # 尝试从查询参数获取
    if websocket.query_params.get("token"):
        token = websocket.query_params.get("token")

    # 尝试从头部获取
    elif "Authorization" in websocket.headers:
        auth_header = websocket.headers["Authorization"]
        if auth_header.startswith("Bearer ") or auth_header.startswith("bearer "):
            token = auth_header[7:]

    if not token:
        await websocket.close(code=1008)
        raise HTTPException(status_code=401, detail="Missing authentication token")

    try:
        payload = jwt.decode(token, jwt_config.secret_key, algorithms=[jwt_config.algorithm])

        username: str = payload.get("sub")
        user_id = payload.get("user_id")

        if username is None or user_id is None:
            await websocket.close(code=1008)
            raise HTTPException(status_code=401, detail="Invalid authentication token")

        # 检查 Redis 中的 access_token
        stored_access_token = redis_handler.get(f"access_token:{user_id}")
        if stored_access_token:
            stored_access_token = stored_access_token

        if stored_access_token != token:
            await websocket.close(code=1008)
            raise HTTPException(status_code=401, detail="Invalid authentication token")

        user =await get_user_by_username(db,username)

        if user is None:
            await websocket.close(code=1008)
            raise HTTPException(status_code=401, detail="User not found")

        return user
    except JWTError as e:

        await websocket.close(code=1008)
        raise HTTPException(status_code=401, detail=f"Invalid authentication token: {str(e)}")
