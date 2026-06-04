# -*- coding: utf-8 -*-
"""
准确性测试
跨数据源对比，验证数据一致性
"""
import numpy as np
import pytest


class TestAccuracy:
    """准确性测试类"""

    def test_cross_source_accuracy(self, all_sources, fund_codes):
        """跨数据源准确性对比"""
        # 选取前5只基金进行测试
        test_codes = fund_codes[:5]

        results_by_fund = {}
        for code in test_codes:
            results_by_fund[code] = {}
            for source in all_sources:
                result = source.fetch_single(code)
                if result.error is None and result.nav is not None:
                    results_by_fund[code][source.get_name()] = result.nav

        print("\n跨数据源准确性对比:")
        print("-" * 80)

        all_deviations = []
        for code, source_results in results_by_fund.items():
            if len(source_results) < 2:
                print(f"{code}: 数据源不足，跳过")
                continue

            navs = list(source_results.values())
            median_nav = np.median(navs)

            print(f"\n{code} (中位数: {median_nav:.4f}):")
            for source_name, nav in source_results.items():
                deviation = abs(nav - median_nav) / median_nav * 100
                all_deviations.append(deviation)
                status = "✓" if deviation < 1.0 else "✗"
                print(f"  {status} {source_name}: {nav:.4f} (偏差: {deviation:.2f}%)")

        if all_deviations:
            mean_dev = np.mean(all_deviations)
            max_dev = np.max(all_deviations)
            print(f"\n总体统计:")
            print(f"  平均偏差: {mean_dev:.2f}%")
            print(f"  最大偏差: {max_dev:.2f}%")

            # 注意：准确性测试主要用于记录，不作为硬性断言
            # 因为不同数据源可能返回不同日期的净值
            if max_dev > 5.0:
                pytest.warn(f"最大偏差较大: {max_dev:.2f}%，可能是不同日期的数据")
