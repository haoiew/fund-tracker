# -*- coding: utf-8 -*-
"""
基金服务测试
"""
import pytest
from decimal import Decimal
import pandas as pd

from app.services.fund_service import FundService
from app.schemas.fund import FundRealtimeData


class TestFundService:
    """基金数据服务测试类"""

    @pytest.fixture
    def fund_service(self):
        """创建基金服务实例"""
        return FundService()

    @pytest.mark.integration
    def test_get_fund_name(self, fund_service):
        """测试获取基金名称"""
        name = fund_service.get_fund_name("000001")
        assert isinstance(name, str)
        assert len(name) > 0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_realtime_data_structure(self, fund_service):
        """测试实时数据返回结构"""
        data = await fund_service.get_realtime_data("000001")
        assert isinstance(data, FundRealtimeData)
        assert data.code == "000001"
        assert hasattr(data, 'name')
        assert hasattr(data, 'estimate_nav')
        assert hasattr(data, 'estimate_change')
        assert hasattr(data, 'status')

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_chart_data(self, fund_service):
        """测试获取图表数据"""
        data = await fund_service.get_chart_data("000001", "1M")
        assert isinstance(data, dict)
        assert 'data' in data

    @pytest.mark.integration
    def test_search_funds(self, fund_service):
        """测试基金搜索"""
        results = fund_service.search_funds("沪深300", limit=5)
        assert isinstance(results, list)
        if results:
            assert 'code' in results[0]
            assert 'name' in results[0]

    def test_search_funds_uses_literal_keyword_for_akshare_fallback(self, fund_service, monkeypatch):
        """基金名称带括号时不应触发 pandas 正则匹配警告。"""
        fund_service.cache.clear()
        monkeypatch.setattr(fund_service, "_search_from_eastmoney", lambda keyword, limit: [])

        class FakeAkshare:
            @staticmethod
            def fund_name_em():
                return pd.DataFrame([
                    {
                        "基金代码": "012345",
                        "基金简称": "南方香港优选股票(QDII-LOF)",
                        "基金类型": "QDII",
                        "基金公司": "南方基金",
                    }
                ])

        import sys
        monkeypatch.setitem(sys.modules, "akshare", FakeAkshare)

        results = fund_service.search_funds("南方香港优选股票(QDII-LOF)", limit=5)

        assert results == [{
            "code": "012345",
            "name": "南方香港优选股票(QDII-LOF)",
            "type": "QDII",
            "company": "南方基金",
        }]

    def test_search_funds_handles_short_alias(self, fund_service, monkeypatch):
        """基金简称缺少中间词时仍应返回可人工确认的候选。"""
        fund_service.cache.clear()
        monkeypatch.setattr(fund_service, "_load_eastmoney_fund_catalog", lambda: [
            {"code": "519674", "name": "银河创新成长混合A", "type": "混合型-偏股", "company": ""},
            {"code": "014143", "name": "银河创新成长混合C", "type": "混合型-偏股", "company": ""},
        ])

        results = fund_service.search_funds("银河创新混合A", limit=5)

        assert results[0]["code"] == "519674"

    def test_search_funds_handles_duplicate_brand_alias(self, fund_service, monkeypatch):
        """截图或平台别名重复品牌词时仍应返回实际基金。"""
        fund_service.cache.clear()
        monkeypatch.setattr(fund_service, "_load_eastmoney_fund_catalog", lambda: [
            {"code": "012709", "name": "东方红中证红利低波动指数C", "type": "指数型-股票", "company": ""},
            {"code": "025518", "name": "东方红中证东方红红利低波动指数D", "type": "指数型-股票", "company": ""},
        ])

        results = fund_service.search_funds("东方红中证东方红红利低波动指数C", limit=5)

        assert results[0]["code"] == "012709"

    def test_get_fund_name_uses_catalog_when_cache_is_empty(self, fund_service, monkeypatch):
        """名称缓存未预热时，应从基金目录解析名称，而不是把代码当名称返回。"""
        if "get_fund_name" in fund_service.__dict__:
            monkeypatch.delattr(fund_service, "get_fund_name")
        fund_service.cache.delete("fund_name:005051")
        fund_service._fund_names_cache.pop("005051", None)
        monkeypatch.setattr(fund_service, "_load_eastmoney_fund_catalog", lambda: [
            {"code": "005051", "name": "摩根标普港股通低波红利指数A", "type": "指数型", "company": ""},
        ])

        assert fund_service.get_fund_name("005051") == "摩根标普港股通低波红利指数A"


class TestFundTrendAnalysis:
    """基金趋势分析测试"""

    @pytest.fixture
    def fund_service(self):
        return FundService()

    @pytest.mark.asyncio
    async def test_screen_funds_params(self, fund_service):
        """测试基金筛选参数处理"""
        results = await fund_service.screen_funds([], 'up', 2, 0.03)
        assert isinstance(results, list)
        assert len(results) == 0

    def test_market_screen_uses_rank_candidates_and_top_limit(self, fund_service, monkeypatch):
        """全市场筛选使用市场候选，并默认限制 Top10。"""
        monkeypatch.setattr(fund_service, "_get_market_rank_candidates", lambda direction, days, screen_type: ["000001", "000002"])

        codes, allow_realtime_proxies, result_limit = fund_service._resolve_screen_codes(
            None, "market", "up", 2, "consecutive"
        )

        assert codes == ["000001", "000002"]
        assert allow_realtime_proxies is False
        assert result_limit == 10

    @pytest.mark.asyncio
    async def test_append_realtime_change_uses_alternative_estimate(self, fund_service, monkeypatch):
        """筛选消费后端已选择且具有真实行情时刻的推测值。"""
        from datetime import datetime, timezone, timedelta
        from app.core import data_contract
        from app.core import data_source
        from app.services import fund_service as service_module
        now = datetime(2026, 10, 13, 14, 30, tzinfo=timezone(timedelta(hours=8)))
        monkeypatch.setattr(data_contract, "shanghai_now", lambda: now)
        monkeypatch.setattr(service_module, "shanghai_now", lambda: now)
        async def fake_realtime(code):
            return FundRealtimeData(
                code=code,
                name="测试基金",
                estimate_change=Decimal("2.5"),
                update_time="2026-10-13 14:29",
                data_kind="holdings_estimate",
                data_kind_label="披露持仓外推",
                is_realtime=False,
                is_inferred=True,
            )

        monkeypatch.setattr(fund_service, "get_realtime_data", fake_realtime)

        hist = pd.DataFrame([
            {"净值日期": pd.Timestamp("2026-06-08"), "累计净值": 1.0, "pct_change": 0.01},
            {"净值日期": pd.Timestamp("2026-06-09"), "累计净值": 1.1, "pct_change": 0.02},
        ])

        enriched = await fund_service._append_realtime_change(hist, "000001", allow_realtime_proxies=True)

        assert len(enriched) == 3
        assert enriched.iloc[-1]["pct_change"] == pytest.approx(0.025)
        assert enriched.iloc[-1]["净值日期"] == pd.Timestamp("2026-10-13")
        assert enriched.iloc[-1]["return_basis"] == "intraday_estimate"

    @pytest.mark.asyncio
    async def test_append_realtime_change_never_counts_today_twice(self, fund_service, monkeypatch):
        from datetime import datetime, timezone, timedelta
        from app.services import fund_service as service_module
        now = datetime(2026, 10, 13, 18, tzinfo=timezone(timedelta(hours=8)))
        monkeypatch.setattr(service_module, "shanghai_now", lambda: now)

        async def must_not_fetch(*args):
            pytest.fail("已有今日正式净值时不应再追加今日估值")

        monkeypatch.setattr(fund_service, "_get_realtime_screen_change", must_not_fetch)
        hist = pd.DataFrame([{"净值日期": pd.Timestamp("2026-10-13"), "单位净值": 1.2, "pct_change": 0.01}])
        result = await fund_service._append_realtime_change(hist, "000001", allow_realtime_proxies=False)
        assert result is hist
        assert len(result) == 1

    def test_analyze_trend_empty_data(self, fund_service):
        """测试空数据的趋势分析"""
        import pandas as pd
        days, pct = fund_service.analyze_trend(pd.DataFrame(), 'up')
        assert days == 0
        assert pct == 0.0
