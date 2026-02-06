# -*- coding: utf-8 -*-
"""
FastAPI应用主入口
"""
import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.api.v1 import api_router
from app.db.base import engine, Base
from app.middleware import setup_error_handlers
from app.logger import get_logger, setup_logging

# 配置日志
logger = get_logger("main")


# 创建数据库表
# 注意：生产环境建议使用Alembic进行数据库迁移
try:
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表创建成功")
except Exception as e:
    logger.error(f"数据库表创建失败: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 启动成功！")
    logger.info(f"📍 服务地址: http://{settings.HOST}:{settings.PORT}")
    logger.info(f"📚 API文档: http://{settings.HOST}:{settings.PORT}/docs")
    
    # 启动调度器和预加载服务
    try:
        from app.services.scheduler_service import scheduler_service
        from app.services.preload_service import preload_service
        from app.config import fund_config
        
        # 启动调度器
        scheduler_service.start()
        
        # 启动预加载（如果启用）
        if getattr(fund_config, 'PRELOAD_ENABLED', True):
            logger.info("🔄 启动数据预加载...")
            await preload_service.start_preload()
        
    except Exception as e:
        logger.error(f"启动调度器/预加载服务失败: {e}")
    
    yield
    
    # 关闭时执行
    try:
        from app.services.scheduler_service import scheduler_service
        scheduler_service.shutdown()
    except Exception as e:
        logger.error(f"关闭调度器失败: {e}")
    
    logger.info("👋 应用关闭")


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    description="基金跟踪器API - 支持实时估值、历史数据、持仓管理、OCR识别",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# 配置全局异常处理
setup_error_handlers(app)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if hasattr(settings, 'CORS_ORIGINS') else ["http://localhost:5173", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    # 运行启动检查
    from app.startup import run_startup_checks
    run_startup_checks()

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
