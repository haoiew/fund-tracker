# -*- coding: utf-8 -*-
"""
通用Pydantic模型
"""
from typing import Generic, TypeVar, Optional, List
from pydantic import BaseModel, Field

T = TypeVar('T')


class ResponseModel(BaseModel, Generic[T]):
    """通用响应模型"""
    code: int = 200
    message: str = "success"
    data: Optional[T] = None


class ListResponse(BaseModel, Generic[T]):
    """列表响应模型"""
    items: List[T]
    total: int
    page: int = 1
    page_size: int = 20


class PaginationParams(BaseModel):
    """分页参数"""
    page: int = 1
    page_size: int = 20
