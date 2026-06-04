# -*- coding: utf-8 -*-
"""
AKShare数据源适配器（基线对照）
使用akshare库获取基金数据，与项目现有方案一致
"""
import time
import sys
from io import StringIO
from typing import List, Optional
from datetime import datetime

import akshare as ak
import pandas as pd

from .base import BaseDataSource, FundDataResult


class AkshareSource(BaseDataSource):
    """AKShare数据源"""

    def __init__(self):
        # 禁用akshare进度条
        import os
        os.environ['TQDM_DISABLE'] = '1'

    def get_name(self) -> str:
        return "akshare"

    def fetch_single(self, code: str) -> FundDataResult:
        start = time.time()

        # 尝试策略1: LOF实时行情
        try:
            old_stdout = sys.stdout
            sys.stdout = StringIO()
            try:
                df = ak.fund_lof_spot_em()
            finally:
                sys.stdout = old_stdout

            row = df[df['代码'] == code]
            if not row.empty:
                duration = (time.time() - start) * 1000
                return self._create_success_result(
                    code=code,
                    name=str(row['名称'].values[0]),
                    nav=float(row['最新价'].values[0]),
                    change_pct=float(row['涨跌幅'].values[0]),
                    update_time=datetime.now().strftime('%Y-%m-%d %H:%M'),
                    raw_data={'source': 'LOF行情'},
                    duration_ms=duration
                )
        except Exception:
            pass

        # 尝试策略2: 最新净值
        try:
            old_stdout = sys.stdout
            sys.stdout = StringIO()
            try:
                df = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
            finally:
                sys.stdout = old_stdout

            if not df.empty:
                latest = df.iloc[-1]
                duration = (time.time() - start) * 1000
                return self._create_success_result(
                    code=code,
                    name=code,
                    nav=float(latest['单位净值']),
                    change_pct=None,
                    update_time=latest['净值日期'].strftime('%Y-%m-%d'),
                    raw_data={'source': '最新净值'},
                    duration_ms=duration
                )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return self._create_error_result(code, str(e), duration)

        duration = (time.time() - start) * 1000
        return self._create_error_result(code, "无数据", duration)

    def fetch_batch(self, codes: List[str]) -> List[FundDataResult]:
        """批量获取 - 尝试使用LOF批量接口"""
        start = time.time()
        results = []

        try:
            old_stdout = sys.stdout
            sys.stdout = StringIO()
            try:
                lof_df = ak.fund_lof_spot_em()
            finally:
                sys.stdout = old_stdout

            # 构建代码索引
            lof_dict = {}
            if lof_df is not None and not lof_df.empty:
                for _, row in lof_df.iterrows():
                    lof_dict[str(row['代码'])] = row

            for code in codes:
                if code in lof_dict:
                    row = lof_dict[code]
                    results.append(self._create_success_result(
                        code=code,
                        name=str(row['名称']),
                        nav=float(row['最新价']),
                        change_pct=float(row['涨跌幅']),
                        update_time=datetime.now().strftime('%Y-%m-%d %H:%M'),
                        raw_data={'source': 'LOF批量'},
                        duration_ms=(time.time() - start) * 1000 / len(codes)
                    ))
                else:
                    # 降级到单个获取
                    results.append(self.fetch_single(code))
        except Exception:
            # 降级到串行获取
            results = [self.fetch_single(c) for c in codes]

        return results
