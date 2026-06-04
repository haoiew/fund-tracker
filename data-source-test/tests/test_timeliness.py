# -*- coding: utf-8 -*-
"""
及时性测试
验证数据更新的及时性
"""
from datetime import datetime, timedelta
import pytest


class TestTimeliness:
    """及时性测试类"""

    def _parse_update_time(self, time_str: str):
        """解析更新时间字符串"""
        if not time_str:
            return None

        # 尝试多种格式
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%Y-%m-%d',
            '%Y/%m/%d %H:%M:%S',
            '%Y/%m/%d',
        ]

        for fmt in formats:
            try:
                return datetime.strptime(str(time_str).strip(), fmt)
            except ValueError:
                continue
        return None

    def _is_trading_hours(self) -> bool:
        """判断是否在交易时段"""
        now = datetime.now()
        # 周末不交易
        if now.weekday() >= 5:
            return False
        # 交易时段: 9:30-15:00
        trading_start = now.replace(hour=9, minute=30, second=0)
        trading_end = now.replace(hour=15, minute=0, second=0)
        return trading_start <= now <= trading_end

    @pytest.mark.parametrize("source_fixture", ["akshare_source", "efinance_source", "eastmoney_source"])
    def test_data_freshness(self, request, source_fixture, fund_codes):
        """测试数据新鲜度"""
        source = request.getfixturevalue(source_fixture)
        code = fund_codes[0]  # 测试第一只基金

        result = source.fetch_single(code)
        if result.error is not None:
            pytest.skip(f"数据获取失败: {result.error}")

        now = datetime.now()
        is_trading = self._is_trading_hours()

        print(f"\n{source.get_name()} 及时性测试:")
        print(f"  基金代码: {code}")
        print(f"  当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  交易时段: {'是' if is_trading else '否'}")
        print(f"  更新时间: {result.update_time}")

        if result.update_time:
            update_dt = self._parse_update_time(result.update_time)
            if update_dt:
                lag = (now - update_dt).total_seconds() / 60
                print(f"  数据延迟: {lag:.1f}分钟")

                if is_trading:
                    # 交易时段：延迟应小于30分钟
                    if lag > 30:
                        pytest.warn(f"交易时段数据延迟较大: {lag:.1f}分钟")
                else:
                    # 非交易时段：数据应是今天的或昨天的
                    if update_dt.date() < (now - timedelta(days=1)).date():
                        pytest.warn(f"数据日期过旧: {update_dt.date()}")
            else:
                print(f"  无法解析更新时间")
