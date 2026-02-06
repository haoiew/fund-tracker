# -*- coding: utf-8 -*-
"""
持仓相关API接口
"""
import asyncio
from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.schemas.portfolio import (
    PortfolioCreate, PortfolioUpdate, PortfolioResponse,
    PortfolioProfitResponse
)
from app.schemas.common import ResponseModel
from app.services.portfolio_service import portfolio_service
from app.services.fund_core_service import get_fund_core_service

router = APIRouter()


@router.post("", response_model=ResponseModel[PortfolioResponse])
async def create_portfolio(
    portfolio: PortfolioCreate,
    user_id: int = 1,  # TODO: 从JWT获取
    db: Session = Depends(get_db)
):
    """添加持仓"""
    db_portfolio = portfolio_service.create_portfolio(db, user_id, portfolio)
    response = portfolio_service.to_response(db_portfolio)
    return ResponseModel(data=response)


@router.get("", response_model=ResponseModel[List[PortfolioResponse]])
async def get_portfolios(
    user_id: int = 1,  # TODO: 从JWT获取
    db: Session = Depends(get_db)
):
    """获取用户所有持仓"""
    portfolios = portfolio_service.get_user_portfolios(db, user_id)
    responses = [portfolio_service.to_response(p) for p in portfolios]
    return ResponseModel(data=responses)


@router.get("/profit", response_model=ResponseModel[PortfolioProfitResponse])
async def get_portfolio_profit(
    user_id: int = 1,  # TODO: 从JWT获取
    db: Session = Depends(get_db)
):
    """获取持仓收益统计"""
    result = portfolio_service.calculate_portfolio_profit(db, user_id)
    return ResponseModel(data=result)


@router.get("/summary", response_model=ResponseModel[dict])
async def get_portfolio_summary(
    user_id: int = 1,  # TODO: 从JWT获取
    db: Session = Depends(get_db)
):
    """获取持仓汇总（包含列表和统计），自动触发历史数据缓存"""
    portfolios = portfolio_service.get_user_portfolios(db, user_id)
    items = [portfolio_service.to_response(p) for p in portfolios]
    profit_data = portfolio_service.calculate_portfolio_profit(db, user_id)

    # 转换为前端期望的格式
    stats = {
        "total_cost": float(profit_data.summary.total_cost),
        "total_value": float(profit_data.summary.total_value),
        "total_profit_loss": float(profit_data.summary.total_profit),
        "total_profit_loss_pct": float(profit_data.summary.total_profit_rate),
        "item_count": profit_data.summary.fund_count
    }

    # 异步预加载持仓基金的历史数据（不阻塞响应）
    fund_codes = [p.fund_code for p in portfolios]
    if fund_codes:
        core_service = get_fund_core_service()
        asyncio.create_task(core_service.preload_fund_history(fund_codes, priority='normal'))

    return ResponseModel(data={
        "items": items,
        "stats": stats
    })


@router.get("/{portfolio_id}", response_model=ResponseModel[PortfolioResponse])
async def get_portfolio(
    portfolio_id: int,
    user_id: int = 1,  # TODO: 从JWT获取
    db: Session = Depends(get_db)
):
    """获取单个持仓详情"""
    portfolio = portfolio_service.get_portfolio(db, portfolio_id, user_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="持仓不存在")
    response = portfolio_service.to_response(portfolio)
    return ResponseModel(data=response)


@router.put("/{portfolio_id}", response_model=ResponseModel[PortfolioResponse])
async def update_portfolio(
    portfolio_id: int,
    portfolio_update: PortfolioUpdate,
    user_id: int = 1,  # TODO: 从JWT获取
    db: Session = Depends(get_db)
):
    """更新持仓"""
    updated = portfolio_service.update_portfolio(db, portfolio_id, user_id, portfolio_update)
    if not updated:
        raise HTTPException(status_code=404, detail="持仓不存在")
    response = portfolio_service.to_response(updated)
    return ResponseModel(data=response)


@router.delete("/{portfolio_id}")
async def delete_portfolio(
    portfolio_id: int,
    user_id: int = 1,  # TODO: 从JWT获取
    db: Session = Depends(get_db)
):
    """删除持仓"""
    success = portfolio_service.delete_portfolio(db, portfolio_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="持仓不存在")
    return ResponseModel(message="删除成功")


@router.post("/refresh", response_model=ResponseModel[dict])
async def refresh_portfolio(
    user_id: int = 1,  # TODO: 从JWT获取
    db: Session = Depends(get_db)
):
    """刷新持仓数据（重新计算收益）"""
    portfolios = portfolio_service.get_user_portfolios(db, user_id)
    items = [portfolio_service.to_response(p) for p in portfolios]
    profit_data = portfolio_service.calculate_portfolio_profit(db, user_id)

    # 转换为前端期望的格式
    stats = {
        "total_cost": float(profit_data.summary.total_cost),
        "total_value": float(profit_data.summary.total_value),
        "total_profit_loss": float(profit_data.summary.total_profit),
        "total_profit_loss_pct": float(profit_data.summary.total_profit_rate),
        "item_count": profit_data.summary.fund_count
    }

    return ResponseModel(data={
        "items": items,
        "stats": stats
    })
