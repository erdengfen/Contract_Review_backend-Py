"""
合同审阅系统 - 重构后的主应用
"""
import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import APP_NAME, APP_VERSION
from app.api.routes import router, init_services

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(title=APP_NAME, version=APP_VERSION)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化系统"""
    logger.info(" 启动合同审阅系统...")
    await init_services()
    logger.info(" 系统初始化完成")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理资源"""
    logger.info("合同审阅系统已关闭")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
