# -*- coding: utf-8 -*-
"""
efinance数据源适配器
efinance是轻量级金融数据接口库，底层调用东方财富API
"""
import time
from typing import List, Optional
from datetime import datetime

from .base import BaseDataSource, FundDataResult


class EfinanceSource(BaseDataSource):
    """efinance数据源"""

    def __init__(self):
        try:
            import efinance as ef
            self.ef = ef
        except ImportError:
            raise ImportError("请安装efinance: pip install efinance")

    def get_name(self) -> str:
        return "efinance"

    def fetch_single(self, code: str) -> FundDataResult:
        start = time.time()

        try:
            # 使用 get_realtime_increase_rate 获取实时涨跌幅
            df = self.ef.fund.get_realtime_increase_rate(fund_codes=[code])
            duration = (time.time() - start) * 1000

            if df is not None and not df.empty:
                row = df.iloc[0]

                # efinance返回的列名：基金代码, 基金名称, 最新净值, 最新净值公开日期, 估算时间, 估算涨跌幅
                name = str(row.get('基金名称', code))

                # 获取净值
                nav = None
                try:
                    val = float(row.get('最新净值', 0))
                    if val > 0:
                        nav = val
                except (ValueError, TypeError):
                    pass

                # 获取涨跌幅
                change_pct = None
                try:
                    val = row.get('估算涨跌幅')
                    if val is not None and str(val) != 'None':
                        change_pct = float(val)
                except (ValueError, TypeError):
                    pass

                # 获取更新时间
                update_time = None
                try:
                    val = row.get('估算时间')
                    if val is not None and str(val) != 'None':
                        update_time = str(val)
                    else:
                        val = row.get('最新净值公开日期')
                        if val is not None:
                            update_time = str(val)
                except:
                    pass

                # 有净值或涨跌幅就认为成功
                if nav is not None or change_pct is not None:
                    return self._create_success_result(
                        code=code,
                        name=name,
                        nav=nav,
                        change_pct=change_pct,
                        update_time=update_time,
                        raw_data=row.to_dict(),
                        duration_ms=duration
                    )
                else:
                    return self._create_error_result(code, "无有效数据", duration)
            else:
                return self._create_error_result(code, "空响应", duration)

        except Exception as e:
            duration = (time.time() - start) * 1000
            return self._create_error_result(code, str(e), duration)

    def fetch_batch(self, codes: List[str]) -> List[FundDataResult]:
        """批量获取 - efinance原生支持批量"""
        start = time.time()
        results = []

        try:
            # 使用efinance批量接口
            df = self.ef.fund.get_realtime_increase_rate(fund_codes=codes)
            duration = (time.time() - start) * 1000

            if df is not None and not df.empty:
                # 构建索引
                df_dict = {}
                for _, row in df.iterrows():
                    code_val = str(row.get('基金代码', ''))
                    df_dict[code_val] = row

                for code in codes:
                    if code in df_dict:
                        row = df_dict[code]
                        name = str(row.get('基金名称', code))

                        # 获取净值
                        nav = None
                        try:
                            val = float(row.get('最新净值', 0))
                            if val > 0:
                                nav = val
                        except (ValueError, TypeError):
                            pass

                        # 获取涨跌幅
                        change_pct = None
                        try:
                            val = row.get('估算涨跌幅')
                            if val is not None and str(val) != 'None':
                                change_pct = float(val)
                        except (ValueError, TypeError):
                            pass

                        # 获取更新时间
                        update_time = None
                        try:
                            val = row.get('估算时间')
                            if val is not None and str(val) != 'None':
                                update_time = str(val)
                            else:
                                val = row.get('最新净值公开日期')
                                if val is not None:
                                    update_time = str(val)
                        except:
                            pass

                        # 有净值或涨跌幅就认为成功
                        if nav is not None or change_pct is not None:
                            results.append(self._create_success_result(
                                code=code,
                                name=name,
                                nav=nav,
                                change_pct=change_pct,
                                update_time=update_time,
                                raw_data=row.to_dict(),
                                duration_ms=duration / len(codes)
                            ))
                        else:
                            results.append(self._create_error_result(code, "无有效数据", duration / len(codes)))
                    else:
                        results.append(self._create_error_result(code, "未在批量结果中找到", duration / len(codes)))
            else:
                # 批量失败，降级到单个获取
                results = [self.fetch_single(c) for c in codes]

        except Exception as e:
            # 降级到单个获取
            results = [self.fetch_single(c) for c in codes]

        return results
