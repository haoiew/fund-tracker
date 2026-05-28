# -*- coding: utf-8 -*-
"""
持仓相关Pydantic模型
"""
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator

_FUND_CODE_RE = re.compile(r'^[0-9A-Za-z]{1,10}$')


def _validate_fund_code_value(v: str) -> str:
    if not v or not v.strip():
        raise ValueError('基金代码不能为空')
    v = v.strip()
    if not _FUND_CODE_RE.match(v):
        raise ValueError('基金代码格式不正确，只能包含数字和字母')
    return v


class PortfolioBase(BaseModel):
    """持仓基础模型"""
    fund_code: str = Field(..., min_length=1, max_length=10, description="基金代码")
    hold_shares: Decimal = Field(default=Decimal('0'), ge=0, description="持有份额")
    cost_amount: Decimal = Field(default=Decimal('0'), ge=0, description="投入金额")
    cost_nav: Optional[Decimal] = Field(None, ge=0, description="成本净值")
    buy_date: Optional[date] = Field(None, description="购买日期")
    remark: Optional[str] = Field(None, max_length=500, description="备注")

    @field_validator('fund_code')
    @classmethod
    def validate_fund_code(cls, v: str) -> str:
        return _validate_fund_code_value(v)


class PortfolioCreate(PortfolioBase):
    """创建持仓"""
    fund_name: Optional[str] = Field(None, max_length=100, description="基金名称")


class PortfolioUpdate(BaseModel):
    """更新持仓"""
    fund_code: Optional[str] = Field(None, min_length=1, max_length=10, description="基金代码")
    fund_name: Optional[str] = Field(None, max_length=100, description="基金名称")
    hold_shares: Optional[Decimal] = Field(None, ge=0, description="持有份额")
    cost_amount: Optional[Decimal] = Field(None, ge=0, description="投入金额")
    cost_nav: Optional[Decimal] = Field(None, ge=0, description="成本净值")
    buy_date: Optional[date] = Field(None, description="购买日期")
    remark: Optional[str] = Field(None, max_length=500, description="备注")

    @field_validator('fund_code')
    @classmethod
    def validate_fund_code(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return _validate_fund_code_value(v)


class PortfolioResponse(PortfolioBase):
    """持仓响应模型"""
    id: int
    fund_name: str = Field(default="", description="基金名称")
    created_at: datetime
    updated_at: Optional[datetime] = None

    # 实时计算字段
    current_nav: Optional[Decimal] = Field(None, description="当前净值")
    current_change: Optional[Decimal] = Field(None, description="当前涨跌幅(%)")
    current_value: Optional[Decimal] = Field(None, description="当前市值")
    profit_amount: Optional[Decimal] = Field(None, description="盈亏金额")
    profit_rate: Optional[Decimal] = Field(None, description="收益率(%)")

    model_config = {"from_attributes": True}


class PortfolioSummary(BaseModel):
    """持仓汇总"""
    total_cost: Decimal = Field(default=Decimal('0'), description="总投入")
    total_value: Decimal = Field(default=Decimal('0'), description="总市值")
    total_profit: Decimal = Field(default=Decimal('0'), description="总盈亏")
    total_profit_rate: Decimal = Field(default=Decimal('0'), description="总收益率(%)")
    fund_count: int = Field(default=0, description="持仓数量")
    up_count: int = Field(default=0, description="上涨数量")
    down_count: int = Field(default=0, description="下跌数量")


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
