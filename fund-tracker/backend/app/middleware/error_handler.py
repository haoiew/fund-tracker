# -*- coding: utf-8 -*-
"""
全局异常处理中间件
统一处理API异常并返回标准错误响应
"""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
import traceback

from app.schemas.common import ResponseModel
from app.logger import get_logger

logger = get_logger("error_handler")


def setup_error_handlers(app: FastAPI):
    """配置全局异常处理器"""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """处理请求参数验证错误"""
        logger.warning(f"参数验证错误: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ResponseModel(
                code=422,
                message="请求参数错误",
                data={"errors": exc.errors()}
            ).model_dump()
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
        """处理数据库错误"""
        logger.error(f"数据库错误: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ResponseModel(
                code=500,
                message="数据库操作失败",
                data=None
            ).model_dump()
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """处理所有未捕获的异常"""
        error_detail = traceback.format_exc()
        logger.error(f"未捕获的异常: {str(exc)}\n{error_detail}")

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ResponseModel(
                code=500,
                message=f"服务器内部错误: {str(exc)}",
                data=None
            ).model_dump()
        )
