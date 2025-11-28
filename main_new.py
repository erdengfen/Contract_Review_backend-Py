"""
合同审阅系统 - 重构后的主应用
"""
import logging
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI,Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from app.core.config import APP_NAME, APP_VERSION
from app.config.config import settings
from app.core.global_init import llm_manager, redis_handler

from app.middlewares.auth import verify_token
from fastapi.responses import FileResponse
from  app.router import (user,
                         contract,
                         chat,
                         review_task,
                         cas_auth,
                         contract_type,
                         prompt_manage,
                         model_configs,
                        session,
                        signboard,
                        comparison_task
                         )

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(title=APP_NAME, version=APP_VERSION)


@app.get('/static/{filename}')
async def get_file(filename: str):
    file_path = f'./{settings.UPLOAD_DIR}/{filename}'
    return FileResponse(file_path)
if not os.path.exists(settings.UPLOAD_DIR):
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
if not os.path.exists(settings.OSS_BUCKET_DIR):
    os.makedirs(settings.OSS_BUCKET_DIR, exist_ok=True)
# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# 鉴权逻辑
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    auth_result = await verify_token(request)
    if auth_result:
        from fastapi.responses import JSONResponse
        return JSONResponse(content=auth_result.model_dump(), status_code=auth_result.code)
    response = await call_next(request)
    return response
# 注册路由 - 已废弃旧的api路由
# app.include_router(router, prefix="/api")

app.mount(
    "/static",
    StaticFiles(directory=settings.UPLOAD_DIR),
    name="static",
)


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化系统"""
    logger.info(" 启动合同审阅系统...")
    # await init_services()  # 已废弃旧的初始化逻辑
    logger.info(" 系统初始化完成")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理资源"""
    logger.info("合同审阅系统已关闭")


app.include_router(user.router, prefix="/api/user", tags=["用户管理"])
app.include_router(session.router, prefix="/api/session", tags=["会话管理"])
app.include_router(contract.router, prefix="/api/contract", tags=["文件上传下载"])
app.include_router(chat.router, prefix="/api/chat", tags=["合同聊天"])
app.include_router(review_task.router, prefix="/api/review_task", tags=["合同审阅"])
app.include_router(comparison_task.router, prefix="/api/comparison_task", tags=["合同比对"])
app.include_router(contract_type.router, prefix="/api/contract_type", tags=["合同类型管理"])
app.include_router(prompt_manage.router, prefix="/api/prompt_manage", tags=["提示词管理"])
app.include_router(model_configs.router, prefix="/api/model_configs", tags=["模型配置管理"])
app.include_router(signboard.router, prefix="/api/signboard", tags=["看板管理"])


app.include_router(cas_auth.router, tags=["CAS认证"])



# if __name__ == "__main__":
#     uvicorn.run(app, host=settings.server.host, port=settings.server.port)
