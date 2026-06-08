# -*- coding: utf-8 -*-
"""
持仓相关Pydantic模型
"""
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

_FUND_CODE_RE = re.compile(r'^[0-9A-Za-z]{1,10}$')
_IMPORT_FUND_CODE_RE = re.compile(r'^[0-9]{6}$')

TransactionType = Literal['buy', 'sell', 'dividend', 'snapshot']


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
    transaction_count: int = Field(default=0, description="关联交易流水数量")

    model_config = {"from_attributes": True}


class PortfolioTransactionBase(BaseModel):
    """交易流水基础模型"""
    transaction_type: TransactionType = Field(..., description="交易类型")
    trade_date: date = Field(default_factory=date.today, description="交易日期")
    shares: Decimal = Field(default=Decimal('0'), ge=0, description="交易份额")
    amount: Decimal = Field(default=Decimal('0'), ge=0, description="交易金额")
    nav: Optional[Decimal] = Field(None, ge=0, description="交易净值")
    fee: Decimal = Field(default=Decimal('0'), ge=0, description="手续费")
    source: str = Field(default="manual", max_length=20, description="来源")
    remark: Optional[str] = Field(None, max_length=500, description="备注")

    @model_validator(mode='after')
    def validate_transaction_numbers(self):
        if self.transaction_type in {'buy', 'sell', 'snapshot'} and self.shares <= 0:
            raise ValueError('买入、卖出或快照交易的份额必须大于0')
        if self.transaction_type in {'buy', 'snapshot'} and self.amount <= 0:
            raise ValueError('买入或快照交易的金额必须大于0')
        if self.transaction_type == 'dividend' and self.amount <= 0:
            raise ValueError('分红金额必须大于0')
        return self


class PortfolioTransactionCreate(PortfolioTransactionBase):
    """创建交易流水"""
    portfolio_id: Optional[int] = Field(None, ge=1, description="持仓ID")
    fund_code: Optional[str] = Field(None, min_length=1, max_length=10, description="基金代码")

    @field_validator('fund_code')
    @classmethod
    def validate_fund_code(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return _validate_fund_code_value(v)

    @model_validator(mode='after')
    def require_target(self):
        if self.portfolio_id is None and not self.fund_code:
            raise ValueError('portfolio_id 和 fund_code 至少需要一个')
        return self


class PortfolioTransactionResponse(PortfolioTransactionBase):
    """交易流水响应"""
    id: int
    portfolio_id: int
    fund_code: str
    fund_name: str = ""
    created_at: datetime
    updated_at: Optional[datetime] = None

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


class AiRecognizeRequest(BaseModel):
    """AI识别持仓截图请求"""
    image_base64: str = Field(..., description="图片base64编码")
    model: str = Field(..., description="AI模型名称")
    base_url: str = Field(..., description="AI API基础URL")
    api_key: str = Field(..., description="AI API密钥")
    prompt: Optional[str] = Field(None, description="自定义提示词")


class AiConnectionTestRequest(BaseModel):
    """AI接口连通性测试请求"""
    model: str = Field(..., description="AI模型名称")
    base_url: str = Field(..., description="AI API基础URL")
    api_key: str = Field(..., description="AI API密钥")
    include_vision: bool = Field(default=False, description="是否同时测试图片输入能力")


class AiConnectionTestResponse(BaseModel):
    """AI接口连通性测试响应"""
    ok: bool = Field(..., description="是否连通")
    latency_ms: Optional[int] = Field(None, description="端到端延迟毫秒")
    vision_latency_ms: Optional[int] = Field(None, description="视觉输入测试延迟毫秒")
    status_code: Optional[int] = Field(None, description="上游HTTP状态码")
    model: str = Field(default="", description="测试模型")
    message: str = Field(default="", description="测试结果说明")


class AiRecognizeHolding(BaseModel):
    """AI识别出的单条持仓"""
    row_index: Optional[int] = Field(None, ge=1, description="截图列表中的行号")
    fund_code: str = Field(default="", description="基金代码")
    fund_name: str = Field(default="", description="基金名称")
    raw_fund_name: str = Field(default="", description="截图中识别到的原始基金名称")
    market_value: float = Field(default=0, description="市值")
    daily_return: float = Field(default=0, description="昨日收益")
    holding_return: float = Field(default=0, description="持有收益")
    holding_return_rate: Optional[float] = Field(None, description="持有收益率")
    match_status: str = Field(default="pending", description="匹配状态: matched/ambiguous/not_found/invalid/pending")
    confidence: int = Field(default=0, ge=0, le=100, description="匹配置信度")
    match_reason: str = Field(default="", description="匹配原因")
    warnings: list[str] = Field(default_factory=list, description="风险提示")
    candidates: list[dict] = Field(default_factory=list, description="候选基金")


class AiRecognizeResponse(BaseModel):
    """AI识别响应"""
    holdings: list[AiRecognizeHolding] = Field(default_factory=list)
    total_value: float = Field(default=0)
    total_holding_return: float = Field(default=0)
    holdings_count: int = Field(default=0)
    expected_count: Optional[int] = Field(None, description="截图中声明的持仓总数")
    warnings: list[str] = Field(default_factory=list, description="整体识别风险提示")
    ai_raw_content: Optional[str] = Field(None, description="AI原始返回内容")


class PortfolioImportHolding(BaseModel):
    """导入预检条目"""
    row_index: Optional[int] = Field(None, ge=1, description="导入源中的行号")
    fund_code: Optional[str] = Field(None, description="基金代码")
    fund_name: str = Field(..., min_length=1, max_length=100, description="基金名称")
    raw_fund_name: Optional[str] = Field(None, max_length=100, description="截图原始基金名称")
    market_value: Decimal = Field(..., gt=0, description="市值")
    daily_return: Decimal = Field(default=Decimal('0'), description="昨日收益")
    holding_return: Decimal = Field(default=Decimal('0'), description="持有收益")
    holding_return_rate: Optional[Decimal] = Field(None, description="持有收益率")
    match_status: Optional[str] = Field(None, description="识别匹配状态")
    confidence: Optional[int] = Field(None, ge=0, le=100, description="识别置信度")
    match_reason: Optional[str] = Field(None, max_length=100, description="匹配原因")

    @field_validator('fund_code')
    @classmethod
    def validate_import_fund_code(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not v.strip():
            return None
        v = v.strip()
        if not _IMPORT_FUND_CODE_RE.match(v):
            raise ValueError('导入基金代码必须是6位数字')
        return v


class PortfolioImportPreviewRequest(BaseModel):
    """导入预检请求"""
    holdings: list[PortfolioImportHolding] = Field(..., min_length=1, max_length=200)
    strict: bool = Field(default=True, description="严格模式，非明确匹配不允许导入")


class PortfolioImportPreviewItem(BaseModel):
    """导入预检结果条目"""
    row_index: Optional[int] = None
    fund_code: str = ""
    fund_name: str
    raw_fund_name: Optional[str] = None
    market_value: Decimal
    daily_return: Decimal = Decimal('0')
    holding_return: Decimal
    holding_return_rate: Optional[Decimal] = None
    estimated_cost: Decimal
    current_nav: Optional[Decimal] = None
    current_change: Optional[Decimal] = None
    estimated_shares: Optional[Decimal] = None
    estimated_cost_nav: Optional[Decimal] = None
    match_status: Optional[str] = None
    confidence: Optional[int] = None
    status: str = Field(..., description="ready/skipped/invalid")
    reason: str = ""
    warnings: list[str] = Field(default_factory=list)


class PortfolioImportPreviewResponse(BaseModel):
    """导入预检响应"""
    items: list[PortfolioImportPreviewItem]
    ready_count: int
    skipped_count: int
    invalid_count: int


class PortfolioImportConfirmRequest(PortfolioImportPreviewRequest):
    """确认导入请求"""
    trade_date: Optional[date] = Field(None, description="导入快照日期，默认当天")


class PortfolioImportConfirmItem(BaseModel):
    """确认导入结果条目"""
    row_index: Optional[int] = None
    fund_code: str = ""
    fund_name: str
    status: str = Field(..., description="success/skipped/failed")
    portfolio_id: Optional[int] = None
    error: Optional[str] = None


class PortfolioImportConfirmResponse(BaseModel):
    """确认导入响应"""
    items: list[PortfolioImportConfirmItem]
    success_count: int
    skipped_count: int
    failed_count: int
