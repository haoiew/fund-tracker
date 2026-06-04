# -*- coding: utf-8 -*-
"""
Tushare Pro数据源适配器
Tushare Pro是官方金融数据API，需要注册获取token
注意：Tushare Pro主要提供T+1的历史净值，不提供实时估值
"""
import time
from typing import List, Optional
from datetime import datetime, timedelta

from .base import BaseDataSource, FundDataResult


class TushareSource(BaseDataSource):
    """Tushare Pro数据源"""

    def __init__(self, token: str):
        try:
            import tushare as ts
            ts.set_token(token)
            self.pro = ts.pro_api()
        except ImportError:
            raise ImportError("请安装tushare: pip install tushare")

    def get_name(self) -> str:
        return "tushare_pro"

    def _to_ts_code(self, code: str) -> str:
        """转换基金代码为Tushare格式
        深圳: 0/1/2/3开头 -> .SZ
        上海: 5开头 -> .SH
        """
        if code.startswith('5'):
            return f"{code}.SH"
        else:
            return f"{code}.SZ"

    def fetch_single(self, code: str) -> FundDataResult:
        start = time.time()
        ts_code = self._to_ts_code(code)

        try:
            # 尝试获取基金净值
            df = self.pro.fund_nav(ts_code=ts_code, market='E')
            duration = (time.time() - start) * 1000

            if df is not None and not df.empty:
                # 按日期排序，取最新
                df = df.sort_values('end_date', ascending=False)
                latest = df.iloc[0]

                # 获取前一日数据计算涨跌幅
                change_pct = None
                if len(df) >= 2:
                    prev = df.iloc[1]
                    try:
                        curr_nav = float(latest.get('unit_nav', 0))
                        prev_nav = float(prev.get('unit_nav', 0))
                        if prev_nav > 0:
                            change_pct = round((curr_nav - prev_nav) / prev_nav * 100, 2)
                    except (ValueError, TypeError):
                        pass

                nav = float(latest.get('unit_nav', 0)) or None
                if nav and nav > 0:
                    return self._create_success_result(
                        code=code,
                        name=None,  # fund_nav不返回名称
                        nav=nav,
                        change_pct=change_pct,
                        update_time=str(latest.get('end_date', '')),
                        raw_data=latest.to_dict(),
                        duration_ms=duration
                    )
                else:
                    return self._create_error_result(code, "无净值数据", duration)
            else:
                return self._create_error_result(code, "空响应", duration)

        except Exception as e:
            duration = (time.time() - start) * 1000
            error_msg = str(e)
            # 检查是否是积分不足
            if "积分" in error_msg or "credits" in error_msg.lower():
                error_msg = f"积分不足: {error_msg}"
            return self._create_error_result(code, error_msg, duration)

    def fetch_batch(self, codes: List[str]) -> List[FundDataResult]:
        """批量获取 - 由于Tushare有频率限制（1次/分钟），使用串行获取"""
        results = []
        for i, code in enumerate(codes):
            result = self.fetch_single(code)
            results.append(result)
            # Tushare有频率限制（1次/分钟），每次请求间隔65秒
            if i < len(codes) - 1:
                time.sleep(65)
        return results

    def get_fund_basic(self, code: str) -> Optional[dict]:
        """获取基金基本信息"""
        try:
            ts_code = self._to_ts_code(code)
            df = self.pro.fund_basic(ts_code=ts_code)
            if df is not None and not df.empty:
                return df.iloc[0].to_dict()
        except Exception:
            pass
        return None

    def check_token_valid(self) -> bool:
        """检查token是否有效"""
        try:
            df = self.pro.fund_basic(exchange='SSE', list_status='L')
            return df is not None and not df.empty
        except Exception:
            return False
