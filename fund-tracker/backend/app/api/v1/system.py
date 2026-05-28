# -*- coding: utf-8 -*-
"""
系统API - 健康检查、缓存统计、调度器状态
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.cache import get_cache
from app.core.scheduler import scheduler_service
from app.services.history_service import get_history_service
from app.schemas.common import ResponseModel
from app.logger import get_logger

router = APIRouter()
logger = get_logger("api.system")


class RefreshRequest(BaseModel):
    codes: Optional[List[str]] = None


@router.get("/health", response_model=ResponseModel[dict])
async def health_check():
    """健康检查"""
    from app.db.base import check_db_health
    components = {"database": check_db_health()}
    components["scheduler"] = {
        "status": "healthy" if scheduler_service.get_status().get("running") else "degraded",
        **scheduler_service.get_status()
    }
    overall = "healthy" if components["database"].get("status") == "healthy" else "unhealthy"
    return ResponseModel(data={"status": overall, "components": components})


@router.get("/cache/stats", response_model=ResponseModel[dict])
async def get_cache_stats():
    """获取缓存统计"""
    return ResponseModel(data=get_cache().get_stats())


@router.get("/scheduler/status", response_model=ResponseModel[dict])
async def get_scheduler_status():
    """获取调度器状态"""
    return ResponseModel(data=scheduler_service.get_status())


@router.post("/scheduler/refresh", response_model=ResponseModel[dict])
async def manual_refresh(request: RefreshRequest):
    """手动触发数据刷新"""
    try:
        result = await scheduler_service.trigger_manual_refresh(request.codes)
        return ResponseModel(data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduler/history/update", response_model=ResponseModel[dict])
async def update_history(request: RefreshRequest):
    """手动更新历史数据"""
    if not request.codes:
        raise HTTPException(status_code=400, detail="请提供基金代码列表")
    history = get_history_service()
    results = []
    for code in request.codes:
        result = await history.incremental_update(code)
        results.append(result)
    return ResponseModel(data={"updated": len([r for r in results if r.get('updated', 0) > 0]), "results": results})
