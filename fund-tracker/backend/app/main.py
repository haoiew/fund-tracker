# -*- coding: utf-8 -*-
"""
FastAPI应用主入口 - 简化版，无Docker/Redis/PostgreSQL依赖
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
from app.logger import get_logger

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 创建数据库表
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表创建成功")
    except Exception as e:
        logger.error(f"数据库表创建失败: {e}")

    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} 启动")
    logger.info(f"服务地址: http://{settings.HOST}:{settings.PORT}")
    logger.info(f"API文档: http://{settings.HOST}:{settings.PORT}/docs")

    # 启动调度器
    try:
        from app.core.scheduler import scheduler_service
        scheduler_service.start(settings.REFRESH_INTERVAL_MINUTES)
    except Exception as e:
        logger.error(f"启动调度器失败: {e}")

    yield

    # 关闭
    try:
        from app.core.scheduler import scheduler_service
        scheduler_service.shutdown()
    except Exception:
        pass
    try:
        from app.services.fund_service import get_fund_service
        get_fund_service().close()
    except Exception:
        pass
    logger.info("应用关闭")


app = FastAPI(
    title=settings.APP_NAME,
    description="基金跟踪器API",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

setup_error_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"name": settings.APP_NAME, "version": settings.APP_VERSION, "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
