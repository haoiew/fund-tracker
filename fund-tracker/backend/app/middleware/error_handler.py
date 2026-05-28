# -*- coding: utf-8 -*-
"""
全局异常处理中间件
优化内容：
1. 添加环境判断，生产环境隐藏敏感信息
2. 细化数据库错误分类
3. 添加请求ID追踪
4. 统一错误响应格式
"""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError, TimeoutError as SQLTimeoutError
import traceback
import uuid
from datetime import datetime

from app.config import settings
from app.schemas.common import ResponseModel
from app.logger import get_logger

logger = get_logger("error_handler")


def get_request_id() -> str:
    """生成请求ID用于追踪"""
    return str(uuid.uuid4())[:8]


def mask_sensitive_info(message: str) -> str:
    """脱敏敏感信息"""
    import re
    # 脱敏手机号
    message = re.sub(r'1[3-9]\d{9}', '1**********', message)
    # 脱敏邮箱
    message = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '***@***.***', message)
    # 脱敏身份证
    message = re.sub(r'\d{17}[\dXx]', '******************', message)
    return message


def setup_error_handlers(app: FastAPI):
    """配置全局异常处理器"""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """处理请求参数验证错误"""
        request_id = get_request_id()
        errors = exc.errors()
        
        # 格式化错误信息
        error_messages = []
        for error in errors:
            field = ".".join(str(loc) for loc in error.get("loc", []))
            msg = error.get("msg", "未知错误")
            error_messages.append(f"{field}: {msg}")
        
        logger.warning(f"[{request_id}] 参数验证错误: {errors}")
        
        # 生产环境不返回详细错误字段
        response_data = {
            "request_id": request_id,
            "timestamp": datetime.now().isoformat()
        }
        
        if settings.DEBUG:
            response_data["errors"] = errors
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ResponseModel(
                code=422,
                message=f"请求参数错误: {'; '.join(error_messages[:3])}",  # 最多显示3个错误
                data=response_data
            ).model_dump()
        )

    @app.exception_handler(IntegrityError)
    async def integrity_exception_handler(request: Request, exc: IntegrityError):
        """处理数据库完整性约束错误"""
        request_id = get_request_id()
        error_msg = str(exc.orig) if hasattr(exc, 'orig') else str(exc)
        
        logger.error(f"[{request_id}] 数据完整性错误: {error_msg}")
        
        # 解析具体约束错误
        message = "数据操作失败"
        if "unique" in error_msg.lower() or "duplicate" in error_msg.lower():
            message = "数据已存在，请勿重复添加"
        elif "foreign key" in error_msg.lower():
            message = "关联数据不存在"
        elif "not null" in error_msg.lower():
            message = "必填字段不能为空"
        
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=ResponseModel(
                code=409,
                message=message,
                data={"request_id": request_id} if settings.DEBUG else None
            ).model_dump()
        )

    @app.exception_handler(OperationalError)
    async def operational_exception_handler(request: Request, exc: OperationalError):
        """处理数据库连接错误"""
        request_id = get_request_id()
        error_msg = str(exc)
        
        logger.error(f"[{request_id}] 数据库连接错误: {error_msg}")
        
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=ResponseModel(
                code=503,
                message="数据库服务暂时不可用，请稍后重试",
                data={"request_id": request_id} if settings.DEBUG else None
            ).model_dump()
        )

    @app.exception_handler(SQLTimeoutError)
    async def db_timeout_exception_handler(request: Request, exc: SQLTimeoutError):
        """处理数据库超时错误"""
        request_id = get_request_id()
        
        logger.error(f"[{request_id}] 数据库查询超时: {str(exc)}")
        
        return JSONResponse(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            content=ResponseModel(
                code=504,
                message="数据库查询超时，请稍后重试",
                data={"request_id": request_id} if settings.DEBUG else None
            ).model_dump()
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
        """处理其他数据库错误"""
        request_id = get_request_id()
        error_detail = traceback.format_exc()
        
        logger.error(f"[{request_id}] 数据库错误: {str(exc)}\n{error_detail}")
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ResponseModel(
                code=500,
                message="数据库操作失败",
                data={"request_id": request_id} if settings.DEBUG else None
            ).model_dump()
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """处理所有未捕获的异常"""
        request_id = get_request_id()
        error_detail = traceback.format_exc()
        error_msg = mask_sensitive_info(str(exc))
        
        logger.error(f"[{request_id}] 未捕获的异常: {error_msg}\n{error_detail}")
        
        # 生产环境隐藏详细错误信息
        if not settings.DEBUG:
            message = "服务器内部错误，请稍后重试"
            response_data = {"request_id": request_id}
        else:
            message = f"服务器内部错误: {error_msg}"
            response_data = {
                "request_id": request_id,
                "error_type": type(exc).__name__,
                "timestamp": datetime.now().isoformat()
            }
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ResponseModel(
                code=500,
                message=message,
                data=response_data
            ).model_dump()
        )
