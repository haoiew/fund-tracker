# -*- coding: utf-8 -*-
"""
调度器和缓存管理 API
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.scheduler_service import scheduler_service
from app.services.preload_service import preload_service
from app.services.task_priority import TaskPriority
from app.services.history_service import history_service
from app.schemas.common import ResponseModel
from app.logger import get_logger

router = APIRouter()
logger = get_logger("api.scheduler")


class RefreshRequest(BaseModel):
    """刷新请求"""
    codes: Optional[List[str]] = None


class WarmupRequest(BaseModel):
    """预热请求"""
    codes: List[str]
    priority: str = "P3"  # P0, P1, P2, P3


class HistoryStatusRequest(BaseModel):
    """历史数据状态请求"""
    codes: List[str]


@router.get("/status", response_model=ResponseModel[dict])
async def get_scheduler_status():
    """获取调度器状态"""
    try:
        status = scheduler_service.get_status()
        preload_stats = preload_service.get_stats()
        
        return ResponseModel(data={
            "scheduler": status,
            "preload": preload_stats,
            "priority_summary": preload_service.get_priority_summary()
        })
    except Exception as e:
        logger.error(f"获取调度器状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh", response_model=ResponseModel[dict])
async def manual_refresh(request: RefreshRequest):
    """手动触发刷新"""
    try:
        result = await scheduler_service.trigger_manual_refresh(request.codes)
        return ResponseModel(data=result)
    except Exception as e:
        logger.error(f"手动刷新失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/warmup", response_model=ResponseModel[dict])
async def warmup_cache(request: WarmupRequest):
    """预热指定基金缓存"""
    try:
        # 解析优先级
        priority_map = {
            "P0": TaskPriority.P0,
            "P1": TaskPriority.P1,
            "P2": TaskPriority.P2,
            "P3": TaskPriority.P3
        }
        priority = priority_map.get(request.priority.upper(), TaskPriority.P3)
        
        result = await preload_service.warmup_cache(request.codes, priority)
        return ResponseModel(data=result)
    except Exception as e:
        logger.error(f"预热缓存失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/portfolio/add/{code}", response_model=ResponseModel[dict])
async def add_to_portfolio(code: str):
    """添加基金到用户持仓（高优先级）"""
    try:
        preload_service.add_to_portfolio(code)
        return ResponseModel(data={
            "code": code,
            "action": "added_to_portfolio",
            "priority": "P0"
        })
    except Exception as e:
        logger.error(f"添加持仓失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/portfolio/remove/{code}", response_model=ResponseModel[dict])
async def remove_from_portfolio(code: str):
    """从用户持仓移除"""
    try:
        preload_service.remove_from_portfolio(code)
        return ResponseModel(data={
            "code": code,
            "action": "removed_from_portfolio"
        })
    except Exception as e:
        logger.error(f"移除持仓失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/history/update", response_model=ResponseModel[dict])
async def update_history_data(request: RefreshRequest):
    """手动更新历史数据"""
    try:
        if not request.codes:
            raise HTTPException(status_code=400, detail="请提供基金代码列表")
        
        results = []
        for code in request.codes:
            result = await history_service.incremental_update(code)
            results.append(result)
        
        return ResponseModel(data={
            "updated": len([r for r in results if r.get('updated', 0) > 0]),
            "results": results
        })
    except Exception as e:
        logger.error(f"更新历史数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/history/status", response_model=ResponseModel[dict])
async def get_history_status(request: HistoryStatusRequest):
    """获取历史数据缓存状态"""
    try:
        statuses = []
        for code in request.codes:
            status = history_service.get_cache_status(code)
            statuses.append(status)
        
        return ResponseModel(data={
            "total": len(statuses),
            "statuses": statuses
        })
    except Exception as e:
        logger.error(f"获取历史数据状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/history/warmup", response_model=ResponseModel[dict])
async def warmup_history(request: RefreshRequest):
    """预热历史数据缓存"""
    try:
        if not request.codes:
            raise HTTPException(status_code=400, detail="请提供基金代码列表")
        
        result = await history_service.warmup_history_cache(
            request.codes,
            days=365  # 默认预热1年数据
        )
        
        return ResponseModel(data=result)
    except Exception as e:
        logger.error(f"预热历史数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache/stats", response_model=ResponseModel[dict])
async def get_cache_stats():
    """获取缓存统计"""
    try:
        from app.services.cache_service import get_cache_service
        cache = get_cache_service()
        stats = cache.get_stats()
        
        return ResponseModel(data=stats)
    except Exception as e:
        logger.error(f"获取缓存统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
