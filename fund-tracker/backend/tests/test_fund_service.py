# -*- coding: utf-8 -*-
"""
基金服务测试
"""
import pytest
from decimal import Decimal

from app.services.fund_service import FundDataService
from app.schemas.fund import FundRealtimeData


class TestFundDataService:
    """基金数据服务测试类"""

    @pytest.fixture
    def fund_service(self):
        """创建基金服务实例"""
        return FundDataService()

    def test_get_fund_name(self, fund_service):
        """测试获取基金名称"""
        # 测试已知基金代码
        name = fund_service.get_fund_name("000001")
        assert isinstance(name, str)
        assert len(name) > 0

    def test_get_realtime_data_structure(self, fund_service):
        """测试实时数据返回结构"""
        data = fund_service.get_realtime_data("000001")
        assert isinstance(data, FundRealtimeData)
        assert data.code == "000001"
        assert hasattr(data, 'name')
        assert hasattr(data, 'estimate_nav')
        assert hasattr(data, 'estimate_change')
        assert hasattr(data, 'status')

    def test_get_chart_data(self, fund_service):
        """测试获取图表数据"""
        data = fund_service.get_chart_data("000001", "1M")
        assert hasattr(data, 'dates')
        assert hasattr(data, 'values')
        assert hasattr(data, 'changes')
        assert isinstance(data.dates, list)
        assert isinstance(data.values, list)

    def test_search_funds(self, fund_service):
        """测试基金搜索"""
        results = fund_service.search_funds("沪深300", limit=5)
        assert isinstance(results, list)
        if results:
            assert 'code' in results[0]
            assert 'name' in results[0]


class TestFundTrendAnalysis:
    """基金趋势分析测试"""

    @pytest.fixture
    def fund_service(self):
        return FundDataService()

    def test_screen_funds_params(self, fund_service):
        """测试基金筛选参数处理"""
        # 测试空列表
        results = fund_service.screen_funds([], 'up', 2, Decimal('0.03'))
        assert isinstance(results, list)
        assert len(results) == 0

    def test_analyze_trend_empty_data(self, fund_service):
        """测试空数据的趋势分析"""
        import pandas as pd
        days, pct = fund_service.analyze_trend(pd.DataFrame(), 'up')
        assert days == 0
        assert pct == Decimal('0')
