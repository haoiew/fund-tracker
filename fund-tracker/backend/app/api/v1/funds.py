# -*- coding: utf-8 -*-
"""
基金相关API接口 - 统一使用 FundCoreService
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
import asyncio

from app.db.base import get_db
from app.schemas.fund import (
    FundResponse, FundRealtimeData, FundTrendScreenResult,
    FundSearchRequest, FundChartData, FundCompareRequest
)
from app.schemas.common import ResponseModel
from app.services.fund_core_service import fund_core_service
from app.services.cache_service import get_cache_service
from app.services.preload_service import preload_service
from app.services.history_service import history_service
from app.config import fund_config, chart_config
from app.logger import get_logger

router = APIRouter()
logger = get_logger("api.funds")

executor = ThreadPoolExecutor(max_workers=4)


def run_sync(func, *args, **kwargs):
    """在线程池中执行同步函数"""
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(executor, func, *args, **kwargs)


@router.get("/list", response_model=ResponseModel[List[str]])
async def get_fund_list():
    """获取基金列表"""
    logger.info("获取基金列表")
    data = fund_core_service.get_fund_list()
    return ResponseModel(data=data)


@router.post("/list/add", response_model=ResponseModel[dict])
async def add_fund(code: str):
    """添加基金"""
    logger.info(f"添加基金: {code}")
    success = fund_core_service.add_fund(code)
    return ResponseModel(data={"code": code, "success": success})


@router.post("/list/remove", response_model=ResponseModel[dict])
async def remove_fund(code: str):
    """移除基金"""
    logger.info(f"移除基金: {code}")
    success = fund_core_service.remove_fund(code)
    return ResponseModel(data={"code": code, "success": success})


@router.get("/realtime/{code}", response_model=ResponseModel[FundRealtimeData])
async def get_fund_realtime(code: str):
    """获取基金实时估值"""
    logger.info(f"获取基金实时估值: {code}")
    data = await run_sync(fund_core_service.get_realtime_data, code)
    return ResponseModel(data=data)


@router.post("/realtime/batch", response_model=ResponseModel[List[FundRealtimeData]])
async def get_funds_realtime(codes: List[str]):
    """批量获取基金实时估值 - 使用真正并发，自动触发历史数据缓存"""
    unique_codes = list(set(codes))
    if len(unique_codes) != len(codes):
        logger.info(f"去除重复基金代码: {len(codes)} -> {len(unique_codes)}")

    logger.info(f"批量获取基金实时估值: {unique_codes}")

    for code in unique_codes:
        preload_service.add_recently_viewed(code)

    # 使用真正的并发异步方法，大幅提升性能
    results = await fund_core_service.get_realtime_batch_async(unique_codes)

    # 异步预加载关注基金的历史数据（不阻塞响应）
    asyncio.create_task(fund_core_service.preload_fund_history(unique_codes, priority='low'))

    return ResponseModel(data=results)


@router.get("/{code}/history", response_model=ResponseModel[dict])
async def get_fund_history(
    code: str,
    range: str = Query("3M", description="时间范围: 1W/1M/3M/6M/1Y/ALL"),
    use_local_cache: bool = Query(True, description="是否使用本地缓存")
):
    """获取基金历史净值数据 - 使用统一服务"""
    logger.info(f"获取基金历史数据: {code}, 范围: {range}, 本地缓存: {use_local_cache}")
    
    result = await history_service.get_chart_data_with_fallback(code, range)
    return ResponseModel(data={
        "data": result['data'],
        "source": result['source'],
        "updating": result.get('updating', False)
    })


@router.post("/search", response_model=ResponseModel[List[dict]])
async def search_funds(request: FundSearchRequest):
    """搜索基金"""
    logger.info(f"搜索基金: {request.keyword}")
    results = await run_sync(fund_core_service.search_funds, request.keyword, request.limit)
    return ResponseModel(data=results)


class FundScreenRequest(BaseModel):
    codes: Optional[List[str]] = None
    min_days: int = 2
    min_pct: float = 0.03


@router.post("/screen/up", response_model=ResponseModel[dict])
async def screen_funds_up(request: FundScreenRequest):
    """筛选连续上涨的基金"""
    logger.info(f"筛选上涨基金: {len(request.codes) if request.codes else '全部'}只, 最小天数: {request.min_days}, 最小幅度: {request.min_pct}")
    results = await run_sync(
        fund_core_service.screen_funds,
        request.codes, 'up', request.min_days, request.min_pct
    )
    return ResponseModel(data={
        "direction": "up",
        "min_days": request.min_days,
        "min_pct": request.min_pct,
        "count": len(results),
        "funds": results
    })


@router.post("/screen/down", response_model=ResponseModel[dict])
async def screen_funds_down(request: FundScreenRequest):
    """筛选连续下跌的基金"""
    logger.info(f"筛选下跌基金: {len(request.codes) if request.codes else '全部'}只, 最小天数: {request.min_days}, 最小幅度: {request.min_pct}")
    results = await run_sync(
        fund_core_service.screen_funds,
        request.codes, 'down', request.min_days, request.min_pct
    )
    return ResponseModel(data={
        "direction": "down",
        "min_days": request.min_days,
        "min_pct": request.min_pct,
        "count": len(results),
        "funds": results
    })


@router.get("/screen/{direction}", response_model=ResponseModel[dict])
async def screen_funds_by_direction(
    direction: str,
    min_days: int = Query(2, description="最小连续天数"),
    min_pct: float = Query(0.03, description="最小累计涨跌幅"),
    codes: Optional[str] = Query(None, description="基金代码列表，逗号分隔")
):
    """
    筛选基金（简化接口）
    
    - direction: up(连续上涨) / down(连续下跌)
    - min_days: 最少连续天数
    - min_pct: 最少累计涨跌幅
    - codes: 可选，指定筛选的基金列表（逗号分隔）
    """
    if direction not in ['up', 'down']:
        raise HTTPException(status_code=400, detail="direction must be 'up' or 'down'")
    
    code_list = codes.split(',') if codes else None
    logger.info(f"筛选{direction}基金: {len(code_list) if code_list else '全部'}只")
    
    results = await run_sync(
        fund_core_service.screen_funds,
        code_list, direction, min_days, min_pct
    )
    
    return ResponseModel(data={
        "direction": direction,
        "min_days": min_days,
        "min_pct": min_pct,
        "count": len(results),
        "funds": results
    })


@router.post("/compare", response_model=ResponseModel[dict])
async def compare_funds(request: FundCompareRequest):
    """对比多只基金 - 使用统一服务"""
    logger.info(f"对比基金: {request.codes}, 范围: {request.range}, 基准: {request.include_benchmark}")
    
    result = await run_sync(
        fund_core_service.get_compare_data,
        request.codes, request.range, request.include_benchmark
    )
    
    return ResponseModel(data=result)


@router.get("/default-list", response_model=ResponseModel[List[str]])
async def get_default_fund_list():
    """获取默认基金列表"""
    return ResponseModel(data=fund_config.DEFAULT_FUNDS)


@router.get("/cache/stats", response_model=ResponseModel[dict])
async def get_cache_stats():
    """获取缓存统计信息"""
    cache = get_cache_service()
    stats = cache.get_stats()
    return ResponseModel(data=stats)
