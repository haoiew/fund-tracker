# -*- coding: utf-8 -*-
"""
基金API - 使用新FundService
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import asyncio

from app.schemas.fund import (
    FundRealtimeData, FundSearchRequest, FundCompareRequest, FundCompareMultiRequest
)
from app.schemas.common import ResponseModel
from app.schemas.portfolio import _validate_fund_code_value
from app.services.fund_service import get_fund_service
from app.services.history_service import get_history_service
from app.config import settings
from app.logger import get_logger

router = APIRouter()
logger = get_logger("api.funds")


@router.get("/list", response_model=ResponseModel[List[str]])
async def get_fund_list():
    return ResponseModel(data=get_fund_service().get_fund_list())


@router.post("/list/add", response_model=ResponseModel[dict])
async def add_fund(code: str):
    success = get_fund_service().add_fund(code)
    return ResponseModel(data={"code": code, "success": success})


@router.post("/list/remove", response_model=ResponseModel[dict])
async def remove_fund(code: str):
    success = get_fund_service().remove_fund(code)
    return ResponseModel(data={"code": code, "success": success})


@router.get("/realtime/{code}", response_model=ResponseModel[FundRealtimeData])
async def get_fund_realtime(code: str):
    code = _validate_fund_code_value(code)
    data = await get_fund_service().get_realtime_data(code)
    return ResponseModel(data=data)


@router.post("/realtime/batch", response_model=ResponseModel[List[FundRealtimeData]])
async def get_funds_realtime(codes: List[str]):
    unique_codes = list(set(codes))
    results = await get_fund_service().get_realtime_batch(unique_codes)
    return ResponseModel(data=results)


@router.get("/{code}/history", response_model=ResponseModel[dict])
async def get_fund_history(code: str, range: str = Query("3M")):
    code = _validate_fund_code_value(code)
    result = await get_history_service().get_chart_data_with_fallback(code, range)
    return ResponseModel(data={"data": result['data'], 'source': result['source'], 'updating': result.get('updating', False)})


@router.post("/search", response_model=ResponseModel[List[dict]])
async def search_funds(request: FundSearchRequest):
    results = get_fund_service().search_funds(request.keyword, request.limit)
    return ResponseModel(data=results)


class FundScreenRequest(BaseModel):
    codes: Optional[List[str]] = None
    min_days: int = 2
    min_pct: float = 0.03


async def _screen_funds(direction: str, request: FundScreenRequest) -> ResponseModel:
    results = await get_fund_service().screen_funds(request.codes, direction, request.min_days, request.min_pct)
    return ResponseModel(data={"direction": direction, "min_days": request.min_days, "min_pct": request.min_pct, "count": len(results), "funds": results})


@router.post("/screen/up", response_model=ResponseModel[dict])
async def screen_funds_up(request: FundScreenRequest):
    return await _screen_funds('up', request)


@router.post("/screen/down", response_model=ResponseModel[dict])
async def screen_funds_down(request: FundScreenRequest):
    return await _screen_funds('down', request)


@router.get("/screen/{direction}", response_model=ResponseModel[dict])
async def screen_funds_by_direction(direction: str, min_days: int = Query(2), min_pct: float = Query(0.03), codes: Optional[str] = Query(None)):
    if direction not in ['up', 'down']:
        raise HTTPException(status_code=400, detail="direction must be 'up' or 'down'")
    code_list = codes.split(',') if codes else None
    results = await get_fund_service().screen_funds(code_list, direction, min_days, min_pct)
    return ResponseModel(data={"direction": direction, "min_days": min_days, "min_pct": min_pct, "count": len(results), "funds": results})


@router.post("/compare", response_model=ResponseModel[dict])
async def compare_funds(request: FundCompareRequest):
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, get_fund_service().get_compare_data, request.codes, request.range, request.include_benchmark)
    return ResponseModel(data=result)


@router.post("/compare/multi", response_model=ResponseModel[dict])
async def compare_funds_multi(request: FundCompareMultiRequest):
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, get_fund_service().get_compare_data_multi, request.codes, request.ranges, request.include_benchmark)
    return ResponseModel(data=result)


@router.get("/default-list", response_model=ResponseModel[List[str]])
async def get_default_fund_list():
    return ResponseModel(data=settings.DEFAULT_FUNDS)


@router.get("/cache/stats", response_model=ResponseModel[dict])
async def get_cache_stats():
    return ResponseModel(data=get_fund_service().cache.get_stats())


class FundHistoryBatchRequest(BaseModel):
    codes: List[str]
    range: str = "3M"


@router.post("/history/batch", response_model=ResponseModel[List[dict]])
async def get_funds_history_batch(request: FundHistoryBatchRequest):
    unique_codes = list(set(request.codes))[:50]
    history = get_history_service()
    sem = asyncio.Semaphore(10)

    async def fetch_one(code: str) -> dict:
        async with sem:
            try:
                result = await history.get_chart_data_with_fallback(code, request.range)
                return {"code": code, "data": result['data'], "source": result['source']}
            except Exception as e:
                return {"code": code, "data": [], "source": "error", "error": str(e)}

    results = await asyncio.gather(*[fetch_one(c) for c in unique_codes])
    return ResponseModel(data=results)


class FundInfoBatchRequest(BaseModel):
    codes: List[str]


@router.post("/info/batch", response_model=ResponseModel[List[dict]])
async def get_funds_info_batch(request: FundInfoBatchRequest):
    fs = get_fund_service()
    results = [{"code": c, "name": fs.get_fund_name(c)} for c in list(dict.fromkeys(request.codes))[:100]]
    return ResponseModel(data=results)
