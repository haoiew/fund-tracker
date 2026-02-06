# -*- coding: utf-8 -*-
from app.schemas.fund import (
    FundBase, FundCreate, FundUpdate, FundResponse,
    FundNavHistoryBase, FundNavHistoryCreate, FundNavHistoryResponse,
    FundRealtimeData, FundTrendScreenResult,
    FundSearchRequest, FundHistoryRequest, FundChartData, FundCompareRequest
)
from app.schemas.portfolio import (
    PortfolioBase, PortfolioCreate, PortfolioUpdate, PortfolioResponse,
    PortfolioSummary, PortfolioProfitDetail, PortfolioProfitResponse
)
from app.schemas.user import (
    UserBase, UserCreate, UserUpdate, UserResponse,
    WechatLoginRequest, WechatLoginResponse, UserSettings
)
from app.schemas.common import (
    ResponseModel, ListResponse, PaginationParams,
    OcrScanRequest, OcrScanResponse, OcrFundMatch, OcrFundExtractResponse
)
