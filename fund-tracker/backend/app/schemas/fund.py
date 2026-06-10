# -*- coding: utf-8 -*-
"""
基金相关Pydantic模型
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field


class FundBase(BaseModel):
    """基金基础模型"""
    code: str = Field(..., description="基金代码", min_length=6, max_length=10)
    name: str = Field(..., description="基金名称", max_length=100)
    fund_type: Optional[str] = Field(None, description="基金类型")
    company: Optional[str] = Field(None, description="基金公司")


class FundCreate(FundBase):
    """创建基金"""
    pass


class FundUpdate(BaseModel):
    """更新基金"""
    name: Optional[str] = None
    fund_type: Optional[str] = None
    company: Optional[str] = None


class FundResponse(FundBase):
    """基金响应模型"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class FundNavHistoryBase(BaseModel):
    """基金历史净值基础模型"""
    fund_code: str
    nav_date: date
    nav: Optional[Decimal] = Field(None, description="单位净值")
    accum_nav: Optional[Decimal] = Field(None, description="累计净值")
    daily_change: Optional[Decimal] = Field(None, description="日涨跌幅(%)")


class FundNavHistoryCreate(FundNavHistoryBase):
    """创建历史净值"""
    pass


class FundNavHistoryResponse(FundNavHistoryBase):
    """历史净值响应模型"""
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class FundRealtimeData(BaseModel):
    """基金实时估值数据"""
    code: str = Field(..., description="基金代码")
    name: str = Field(..., description="基金名称")
    estimate_nav: Optional[Decimal] = Field(None, description="估算净值")
    estimate_change: Optional[Decimal] = Field(None, description="估算涨跌幅(%)")
    update_time: str = Field(default="--", description="估值更新时间")
    status: str = Field(default="获取中", description="数据状态")
    data_source: str = Field(default="unknown", description="数据来源")
    data_source_display_name: Optional[str] = Field(None, description="数据来源中文名称")
    data_source_short_name: Optional[str] = Field(None, description="数据来源短名称")
    data_source_description: Optional[str] = Field(None, description="数据来源说明")
    data_kind: str = Field(default="latest_nav", description="数据类型: realtime_estimate/latest_nav")
    data_kind_label: str = Field(default="最新净值", description="数据类型显示名称")
    is_realtime: bool = Field(default=False, description="是否为盘中实时估值")
    data_timestamp: Optional[str] = Field(None, description="数据获取时间戳")
    # 新增字段
    previous_nav: Optional[Decimal] = Field(None, description="昨日净值")
    accumulated_nav: Optional[Decimal] = Field(None, description="累计净值")
    daily_growth: Optional[Decimal] = Field(None, description="日增长率(%)")


class FundTrendScreenResult(BaseModel):
    """基金趋势筛选结果"""
    code: str
    name: str
    days: int = Field(..., description="连续天数")
    pct: Decimal = Field(..., description="累计涨跌幅(%)")

class PeriodScreenRequest(BaseModel):
    """N天内累计涨跌幅筛选请求"""
    codes: Optional[List[str]] = Field(None, description="基金代码列表，为空则筛选全部")
    direction: str = Field(default='up', description="方向: up=上涨, down=下跌")
    period_days: int = Field(default=7, ge=1, le=90, description="统计天数")
    min_pct: float = Field(default=0.03, ge=0, le=1, description="最小涨跌幅（小数形式）")
    include_realtime: bool = Field(default=False, description="是否包含今日实时估值")
    calendar_days: bool = Field(default=False, description="是否按自然日计算（默认按交易日）")
    universe: str = Field(default="local", description="筛选范围: local=传入/本地列表, market=全市场")
    limit: Optional[int] = Field(default=None, ge=1, le=100, description="返回数量上限")


class FundSearchRequest(BaseModel):
    """基金搜索请求"""
    keyword: str = Field(..., description="搜索关键词", min_length=1, max_length=50)
    limit: int = Field(default=10, ge=1, le=50, description="返回数量限制")


class FundHistoryRequest(BaseModel):
    """基金历史数据请求"""
    code: str
    range: str = Field(default="3M", description="时间范围: 1W/1M/3M/6M/1Y/ALL")


class FundChartData(BaseModel):
    """基金图表数据"""
    dates: List[str]
    values: List[Decimal]
    changes: List[Optional[Decimal]]


class FundCompareRequest(BaseModel):
    """基金对比请求"""
    codes: List[str] = Field(..., min_length=1, max_length=10)
    range: str = Field(default="3M", description="时间范围")
    include_benchmark: bool = Field(default=True, description="是否包含基准指数")


class FundCompareMultiRequest(BaseModel):
    """基金多周期对比请求"""
    codes: List[str] = Field(..., min_length=1, max_length=10)
    ranges: List[str] = Field(default_factory=lambda: ["1W", "1M", "3M", "6M", "1Y"], min_length=1, max_length=12)
    include_benchmark: bool = Field(default=True, description="是否包含基准指数")
