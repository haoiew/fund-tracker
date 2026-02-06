# -*- coding: utf-8 -*-
"""
通用Pydantic模型
"""
from typing import Generic, TypeVar, Optional, List
from pydantic import BaseModel, Field

T = TypeVar('T')


class ResponseModel(BaseModel, Generic[T]):
    """通用响应模型"""
    code: int = 200
    message: str = "success"
    data: Optional[T] = None


class ListResponse(BaseModel, Generic[T]):
    """列表响应模型"""
    items: List[T]
    total: int
    page: int = 1
    page_size: int = 20


class PaginationParams(BaseModel):
    """分页参数"""
    page: int = 1
    page_size: int = 20


class OcrScanRequest(BaseModel):
    """OCR扫描请求"""
    image_base64: str = Field(..., description="Base64编码的图片")


class OcrScanResponse(BaseModel):
    """OCR扫描响应"""
    fund_codes: List[str] = Field(default=[], description="识别的基金代码")
    fund_names: List[str] = Field(default=[], description="识别的基金名称")
    raw_text: str = Field(default="", description="原始识别文本")
    confidence: float = Field(default=0.0, description="置信度")


class OcrFundMatch(BaseModel):
    """OCR基金匹配结果"""
    extracted_text: str
    matched_fund: Optional[dict] = None
    confidence: float


class OcrFundExtractResponse(BaseModel):
    """OCR基金提取响应"""
    matches: List[OcrFundMatch]
    total_found: int


class OcrPosition(BaseModel):
    """OCR识别的持仓数据"""
    fund_name: str = Field(..., description="基金名称")
    fund_code: Optional[str] = Field(None, description="基金代码")
    market_value: Optional[float] = Field(None, description="当前市值")
    profit_amount: Optional[float] = Field(None, description="持有收益金额")
    profit_rate: Optional[float] = Field(None, description="持有收益率")
    hold_shares: Optional[float] = Field(None, description="持有份额")
    cost_nav: Optional[float] = Field(None, description="成本净值")
    current_nav: Optional[float] = Field(None, description="当前净值")
    cost_basis: Optional[float] = Field(None, description="成本金额")
    confidence: float = Field(0.8, description="识别置信度")


class OcrPositionExtractResponse(BaseModel):
    """OCR持仓提取响应"""
    positions: List[OcrPosition] = Field(default=[], description="识别的持仓列表")
    total_count: int = Field(0, description="总识别数量")
    matched_count: int = Field(0, description="成功匹配基金代码的数量")
    raw_result: Optional[OcrScanResponse] = Field(None, description="原始识别结果")
