# -*- coding: utf-8 -*-
"""
可行性测试
验证每个数据源能否返回有效数据
"""
import pytest
from sources.base import FundDataResult


class TestFeasibility:
    """可行性测试类"""

    def test_akshare_single(self, akshare_source, fund_codes):
        """测试AKShare单只基金获取"""
        code = fund_codes[0]
        result = akshare_source.fetch_single(code)
        assert result.error is None, f"获取失败: {result.error}"
        assert result.nav is not None, "净值不应为None"
        assert result.nav > 0, "净值应大于0"

    def test_efinance_single(self, efinance_source, fund_codes):
        """测试efinance单只基金获取"""
        code = fund_codes[0]
        result = efinance_source.fetch_single(code)
        assert result.error is None, f"获取失败: {result.error}"
        assert result.nav is not None, "净值不应为None"

    def test_tushare_single(self, tushare_source, fund_codes):
        """测试Tushare单只基金获取"""
        code = fund_codes[0]
        result = tushare_source.fetch_single(code)
        assert result.error is None, f"获取失败: {result.error}"
        assert result.nav is not None, "净值不应为None"

    def test_eastmoney_single(self, eastmoney_source, fund_codes):
        """测试自维护API单只基金获取"""
        code = fund_codes[0]
        result = eastmoney_source.fetch_single(code)
        assert result.error is None, f"获取失败: {result.error}"
        assert result.nav is not None, "净值不应为None"

    @pytest.mark.parametrize("source_fixture", ["akshare_source", "efinance_source", "tushare_source", "eastmoney_source"])
    def test_batch_feasibility(self, request, source_fixture, fund_codes):
        """测试批量获取可行性"""
        source = request.getfixturevalue(source_fixture)
        results = source.fetch_batch(fund_codes)

        success_count = sum(1 for r in results if r.error is None)
        success_rate = success_count / len(fund_codes)

        # 打印详细结果
        print(f"\n{source.get_name()} 批量获取结果:")
        print(f"  总数: {len(fund_codes)}")
        print(f"  成功: {success_count}")
        print(f"  成功率: {success_rate:.1%}")

        # 失败的基金
        failed = [r for r in results if r.error is not None]
        if failed:
            print(f"  失败列表:")
            for r in failed[:5]:  # 只显示前5个
                print(f"    {r.code}: {r.error}")

        # 成功率标准：>= 80%
        assert success_rate >= 0.8, f"成功率过低: {success_rate:.1%}"
