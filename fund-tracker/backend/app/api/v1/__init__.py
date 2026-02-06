# -*- coding: utf-8 -*-
from fastapi import APIRouter

from app.api.v1 import funds, portfolio, ocr, scheduler

api_router = APIRouter()

api_router.include_router(funds.router, prefix="/funds", tags=["基金"])
api_router.include_router(portfolio.router, prefix="/portfolio", tags=["持仓"])
api_router.include_router(ocr.router, prefix="/ocr", tags=["OCR识别"])
api_router.include_router(scheduler.router, prefix="/scheduler", tags=["调度器"])
