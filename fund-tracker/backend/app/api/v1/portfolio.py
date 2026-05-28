# -*- coding: utf-8 -*-
"""
持仓API - 单用户本地工具
"""
import asyncio
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.schemas.portfolio import (
    PortfolioCreate, PortfolioUpdate, PortfolioResponse, PortfolioProfitResponse
)
from app.schemas.common import ResponseModel
from app.services.portfolio_service import portfolio_service
from app.logger import get_logger

router = APIRouter()
logger = get_logger("api.portfolio")


async def _build_portfolio_summary(db: Session) -> dict:
    """Shared helper for summary and refresh endpoints."""
    from app.services.fund_service import get_fund_service
    portfolios = portfolio_service.get_all_portfolios(db)

    # Fetch realtime data once for all funds
    codes = [p.fund_code for p in portfolios]
    rt_list = await get_fund_service().get_realtime_batch(codes)
    rt_map = {code: rt for code, rt in zip(codes, rt_list)}

    items = await asyncio.gather(*[portfolio_service.to_response(p, rt_map.get(p.fund_code)) for p in portfolios])
    profit_data = await portfolio_service.calculate_portfolio_profit(db, rt_map)
    stats = {
        "total_cost": float(profit_data.summary.total_cost),
        "total_value": float(profit_data.summary.total_value),
        "total_profit_loss": float(profit_data.summary.total_profit),
        "total_profit_loss_pct": float(profit_data.summary.total_profit_rate),
        "item_count": profit_data.summary.fund_count
    }
    return {"items": items, "stats": stats}


@router.post("", response_model=ResponseModel[PortfolioResponse])
async def create_portfolio(portfolio: PortfolioCreate, db: Session = Depends(get_db)):
    db_portfolio = portfolio_service.create_portfolio(db, portfolio)
    return ResponseModel(data=await portfolio_service.to_response(db_portfolio))


@router.get("", response_model=ResponseModel[List[PortfolioResponse]])
async def get_portfolios(db: Session = Depends(get_db)):
    portfolios = portfolio_service.get_all_portfolios(db)
    items = await asyncio.gather(*[portfolio_service.to_response(p) for p in portfolios])
    return ResponseModel(data=list(items))


@router.get("/profit", response_model=ResponseModel[PortfolioProfitResponse])
async def get_portfolio_profit(db: Session = Depends(get_db)):
    return ResponseModel(data=await portfolio_service.calculate_portfolio_profit(db))


@router.get("/summary", response_model=ResponseModel[dict])
async def get_portfolio_summary(db: Session = Depends(get_db)):
    return ResponseModel(data=await _build_portfolio_summary(db))


@router.get("/{portfolio_id}", response_model=ResponseModel[PortfolioResponse])
async def get_portfolio(portfolio_id: int, db: Session = Depends(get_db)):
    p = portfolio_service.get_portfolio(db, portfolio_id)
    if not p:
        raise HTTPException(status_code=404, detail="持仓不存在")
    return ResponseModel(data=await portfolio_service.to_response(p))


@router.put("/{portfolio_id}", response_model=ResponseModel[PortfolioResponse])
async def update_portfolio(portfolio_id: int, portfolio_update: PortfolioUpdate, db: Session = Depends(get_db)):
    updated = portfolio_service.update_portfolio(db, portfolio_id, portfolio_update)
    if not updated:
        raise HTTPException(status_code=404, detail="持仓不存在")
    return ResponseModel(data=await portfolio_service.to_response(updated))


@router.delete("/{portfolio_id}")
async def delete_portfolio(portfolio_id: int, db: Session = Depends(get_db)):
    if not portfolio_service.delete_portfolio(db, portfolio_id):
        raise HTTPException(status_code=404, detail="持仓不存在")
    return ResponseModel(message="删除成功")


@router.post("/refresh", response_model=ResponseModel[dict])
async def refresh_portfolio(db: Session = Depends(get_db)):
    return ResponseModel(data=await _build_portfolio_summary(db))
