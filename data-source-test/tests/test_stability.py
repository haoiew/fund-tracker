# -*- coding: utf-8 -*-
"""
稳定性测试
多次调用验证数据源的一致性
"""
import time
import numpy as np
import pytest


class TestStability:
    """稳定性测试类"""

    @pytest.mark.parametrize("source_fixture", ["akshare_source", "efinance_source", "eastmoney_source"])
    def test_stability_rounds(self, request, source_fixture, fund_codes):
        """测试多轮稳定性"""
        source = request.getfixturevalue(source_fixture)
        rounds = 3  # 测试轮数
        interval = 10  # 间隔秒数

        rounds_results = []
        for i in range(rounds):
            results = source.fetch_batch(fund_codes)
            success_count = sum(1 for r in results if r.error is None)
            success_rate = success_count / len(fund_codes)
            avg_time = np.mean([r.fetch_duration_ms for r in results if r.fetch_duration_ms > 0])

            rounds_results.append({
                "round": i + 1,
                "success_rate": success_rate,
                "avg_time_ms": avg_time
            })

            if i < rounds - 1:
                time.sleep(interval)

        # 计算稳定性指标
        success_rates = [r["success_rate"] for r in rounds_results]
        mean_rate = np.mean(success_rates)
        std_rate = np.std(success_rates)

        print(f"\n{source.get_name()} 稳定性测试结果:")
        for r in rounds_results:
            print(f"  第{r['round']}轮: 成功率={r['success_rate']:.1%}, 平均耗时={r['avg_time_ms']:.0f}ms")
        print(f"  平均成功率: {mean_rate:.1%}")
        print(f"  成功率标准差: {std_rate:.2%}")

        # 稳定性标准：成功率标准差 < 15%
        assert std_rate < 0.15, f"稳定性不足，成功率标准差: {std_rate:.2%}"
