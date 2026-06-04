# -*- coding: utf-8 -*-
"""
批量性能测试
测试批量获取的性能表现
"""
import time
import numpy as np
import pytest


class TestBatchPerformance:
    """批量性能测试类"""

    @pytest.mark.parametrize("source_fixture", ["akshare_source", "efinance_source", "tushare_source", "eastmoney_source"])
    def test_batch_timing(self, request, source_fixture, fund_codes):
        """测试批量获取耗时"""
        source = request.getfixturevalue(source_fixture)

        start = time.time()
        results = source.fetch_batch(fund_codes)
        total_ms = (time.time() - start) * 1000

        success_count = sum(1 for r in results if r.error is None)
        durations = [r.fetch_duration_ms for r in results if r.fetch_duration_ms > 0]

        print(f"\n{source.get_name()} 批量性能测试:")
        print(f"  基金数量: {len(fund_codes)}")
        print(f"  总耗时: {total_ms:.0f}ms ({total_ms/1000:.1f}秒)")
        print(f"  平均每只: {total_ms/len(fund_codes):.0f}ms")
        print(f"  成功数量: {success_count}")

        if durations:
            print(f"  单次平均: {np.mean(durations):.0f}ms")
            print(f"  单次最大: {np.max(durations):.0f}ms")
            print(f"  单次最小: {np.min(durations):.0f}ms")

        # 性能标准：批量获取应小于60秒
        assert total_ms < 60000, f"批量获取过慢: {total_ms:.0f}ms"

    @pytest.mark.parametrize("source_fixture", ["efinance_source", "eastmoney_source"])
    def test_single_timing(self, request, source_fixture, fund_codes):
        """测试单次获取耗时"""
        source = request.getfixturevalue(source_fixture)
        code = fund_codes[0]

        # 多次测试取平均
        times = []
        for _ in range(3):
            start = time.time()
            result = source.fetch_single(code)
            duration = (time.time() - start) * 1000
            times.append(duration)
            time.sleep(1)

        avg_time = np.mean(times)

        print(f"\n{source.get_name()} 单次性能测试:")
        print(f"  基金代码: {code}")
        print(f"  平均耗时: {avg_time:.0f}ms")
        print(f"  最大耗时: np.max(times):.0f}ms")

        # 性能标准：单次获取应小于5秒
        assert avg_time < 5000, f"单次获取过慢: {avg_time:.0f}ms"
