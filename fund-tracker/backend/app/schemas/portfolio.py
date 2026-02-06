# -*- coding: utf-8 -*-
"""
持仓相关Pydantic模型
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class PortfolioBase(BaseModel):
    """持仓基础模型"""
    fund_code: str = Field(..., description="基金代码")
    hold_shares: Decimal = Field(default=0, description="持有份额")
    cost_amount: Decimal = Field(default=0, description="投入金额")
    cost_nav: Optional[Decimal] = Field(None, description="成本净值")
    buy_date: Optional[date] = Field(None, description="购买日期")
    remark: Optional[str] = Field(None, description="备注")


class PortfolioCreate(PortfolioBase):
    """创建持仓"""
    pass


class PortfolioUpdate(BaseModel):
    """更新持仓"""
    hold_shares: Optional[Decimal] = None
    cost_amount: Optional[Decimal] = None
    cost_nav: Optional[Decimal] = None
    buy_date: Optional[date] = None
    remark: Optional[str] = None


class PortfolioResponse(PortfolioBase):
    """持仓响应模型"""
    id: int
    user_id: int
    fund_name: str = Field(..., description="基金名称")
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # 实时计算字段
    current_nav: Optional[Decimal] = Field(None, description="当前净值")
    current_change: Optional[Decimal] = Field(None, description="当前涨跌幅(%)")
    current_value: Optional[Decimal] = Field(None, description="当前市值")
    profit_amount: Optional[Decimal] = Field(None, description="盈亏金额")
    profit_rate: Optional[Decimal] = Field(None, description="收益率(%)")
    
    class Config:
        from_attributes = True


class PortfolioSummary(BaseModel):
    """持仓汇总"""
    total_cost: Decimal = Field(..., description="总投入")
    total_value: Decimal = Field(..., description="总市值")
    total_profit: Decimal = Field(..., description="总盈亏")
    total_profit_rate: Decimal = Field(..., description="总收益率(%)")
    fund_count: int = Field(..., description="持有基金数量")
    up_count: int = Field(..., description="上涨基金数量")
    down_count: int = Field(..., description="下跌基金数量")


class PortfolioProfitDetail(BaseModel):
    """持仓收益详情"""
    fund_code: str
    fund_name: str
    cost_amount: Decimal
    current_value: Decimal
    profit_amount: Decimal
    profit_rate: Decimal
    daily_profit: Optional[Decimal] = Field(None, description="当日收益")


class PortfolioProfitResponse(BaseModel):
    """持仓收益响应"""
    summary: PortfolioSummary
    details: list[PortfolioProfitDetail]
