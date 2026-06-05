# -*- coding: utf-8 -*-
"""
基金核心服务 - 统一管理基金数据
合并原FundCoreService + FundDataSourceManager
使用新的DataSourceManager（efinance+eastmoney_direct）和MemoryCache
"""
import asyncio
import json
import time
import os
import re
import threading
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path

import pandas as pd
import numpy as np
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.config import settings
from app.core.cache import get_cache
from app.core.data_source import get_data_source, FundDataResult
from app.schemas.fund import FundRealtimeData
from app.logger import get_logger

logger = get_logger("fund_service")

os.environ['TQDM_DISABLE'] = '1'


class FundService:
    """基金核心服务单例"""

    _instance: Optional['FundService'] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.cache = get_cache()
        self._data_source = get_data_source()
        self._fund_names_cache: Dict[str, str] = {}

        self.session = requests.Session()
        retries = Retry(total=2, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
        self.session.mount('http://', HTTPAdapter(max_retries=retries))
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        self._init_fund_list()

    def _init_fund_list(self):
        self._fund_list: List[str] = []
        fund_file = settings.fund_file_abs_path

        if os.path.exists(fund_file):
            with open(fund_file, 'r', encoding='utf-8') as f:
                self._fund_list = [line.strip() for line in f if line.strip()]
        else:
            self._fund_list = settings.DEFAULT_FUNDS.copy()
            self.save_fund_list()

        logger.info(f"基金列表已加载: {len(self._fund_list)} 只")

    def save_fund_list(self):
        try:
            with open(settings.fund_file_abs_path, 'w', encoding='utf-8') as f:
                for code in self._fund_list:
                    f.write(f"{code}\n")
        except Exception as e:
            logger.error(f"保存基金列表失败: {e}")

    def get_fund_list(self) -> List[str]:
        return self._fund_list.copy()

    def get_fund_codes(self) -> List[str]:
        return self._fund_list.copy()

    def add_fund(self, code: str) -> bool:
        code = str(code).strip()
        if code not in self._fund_list:
            self._fund_list.append(code)
            self.save_fund_list()
            return True
        return False

    def remove_fund(self, code: str) -> bool:
        code = str(code).strip()
        if code in self._fund_list:
            self._fund_list.remove(code)
            self.save_fund_list()
            return True
        return False

    def get_fund_name(self, code: str) -> str:
        if code in self._fund_names_cache:
            return self._fund_names_cache[code]
        cached = self.cache.get(f"fund_name:{code}")
        if cached:
            self._fund_names_cache[code] = cached
            return cached
        return code

    async def get_realtime_data(self, code: str) -> FundRealtimeData:
        """获取单只基金实时数据"""
        cache_key = f"realtime:{code}"
        cached = self.cache.get(cache_key)
        if cached and isinstance(cached, FundRealtimeData):
            return cached

        name = self.get_fund_name(code)
        result = await self._data_source.fetch_single(code)

        if result.is_success:
            rt = FundRealtimeData(
                code=code,
                name=result.name or name,
                estimate_nav=Decimal(str(result.nav)) if result.nav else None,
                estimate_change=Decimal(str(result.change_pct)) if result.change_pct else None,
                update_time=result.update_time or '--',
                status='正常',
                data_source=result.source,
            )
            if result.name and result.name != code:
                self._fund_names_cache[code] = result.name
                self.cache.set(f"fund_name:{code}", result.name, settings.FUND_INFO_CACHE_TTL)
        else:
            rt = FundRealtimeData(
                code=code, name=name,
                status='获取失败',
                data_source=result.source or 'unknown'
            )

        self.cache.set(cache_key, rt, settings.REALTIME_CACHE_TTL)
        return rt

    async def get_realtime_batch(self, codes: List[str]) -> List[FundRealtimeData]:
        """批量获取实时数据"""
        if not codes:
            return []

        results = []
        uncached_codes = []
        uncached_indices = []

        for i, code in enumerate(codes):
            cached = self.cache.get(f"realtime:{code}")
            if cached and isinstance(cached, FundRealtimeData):
                results.append(cached)
            else:
                results.append(None)
                uncached_codes.append(code)
                uncached_indices.append(i)

        if uncached_codes:
            ds_results = await self._data_source.fetch_batch(uncached_codes)
            for idx, result in zip(uncached_indices, ds_results):
                code = codes[idx]
                name = self.get_fund_name(code)

                if result.is_success:
                    rt = FundRealtimeData(
                        code=code,
                        name=result.name or name,
                        estimate_nav=Decimal(str(result.nav)) if result.nav else None,
                        estimate_change=Decimal(str(result.change_pct)) if result.change_pct else None,
                        update_time=result.update_time or '--',
                        status='正常',
                        data_source=result.source,
                    )
                    if result.name and result.name != code:
                        self._fund_names_cache[code] = result.name
                        self.cache.set(f"fund_name:{code}", result.name, settings.FUND_INFO_CACHE_TTL)
                else:
                    rt = FundRealtimeData(
                        code=code, name=name,
                        status='获取失败',
                        data_source=result.source or 'unknown'
                    )
                results[idx] = rt
                self.cache.set(f"realtime:{code}", rt, settings.REALTIME_CACHE_TTL)

        return results

    def get_historical_nav(self, code: str, days: int = 365, max_retries: int = 2) -> pd.DataFrame:
        """获取历史净值"""
        cache_key = f"nav_history:{code}:{days}"
        cached = self.cache.get(cache_key)
        if cached is not None and isinstance(cached, pd.DataFrame) and not cached.empty:
            return cached

        df = self._get_historical_from_eastmoney(code, days, max_retries)
        if not df.empty:
            self.cache.set(cache_key, df, settings.HISTORY_CACHE_TTL)
            return df

        try:
            import akshare as ak
            import sys, io
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()
            try:
                df = ak.fund_open_fund_info_em(symbol=code, indicator="累计净值走势")
            finally:
                sys.stdout = old_stdout

            if df is not None and not df.empty:
                df['净值日期'] = pd.to_datetime(df['净值日期'])
                df['累计净值'] = pd.to_numeric(df['累计净值'])
                df = df.sort_values('净值日期').reset_index(drop=True)
                df['pct_change'] = df['累计净值'].pct_change().fillna(0)
                if days > 0:
                    start_date = datetime.now() - timedelta(days=days)
                    df = df[df['净值日期'] >= start_date]
                self.cache.set(cache_key, df, settings.HISTORY_CACHE_TTL)
                return df
        except Exception as e:
            logger.debug(f"AKShare获取历史净值失败 {code}: {e}")

        return pd.DataFrame()

    def _get_historical_from_eastmoney(self, code: str, days: int, max_retries: int) -> pd.DataFrame:
        for attempt in range(max_retries):
            try:
                url = f"http://fund.eastmoney.com/pingzhongdata/{code}.js"
                resp = self.session.get(url, timeout=10)
                if resp.status_code != 200:
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    return pd.DataFrame()

                match = re.search(r'Data_netWorthTrend\s*=\s*(\[.*?\]);', resp.text, re.DOTALL)
                if not match:
                    return pd.DataFrame()
                data = json.loads(match.group(1))
                if not data:
                    return pd.DataFrame()

                df = pd.DataFrame(data)
                df['x'] = pd.to_datetime(df['x'], unit='ms')
                df['y'] = pd.to_numeric(df['y'])
                df = df.rename(columns={'x': '净值日期', 'y': '累计净值'})
                df = df.sort_values('净值日期').reset_index(drop=True)
                df['pct_change'] = df['累计净值'].pct_change().fillna(0)
                if days > 0:
                    start_date = datetime.now() - timedelta(days=days)
                    df = df[df['净值日期'] >= start_date]
                return df
            except Exception:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
        return pd.DataFrame()

    async def get_chart_data(self, code: str, range_str: str = "3M") -> Dict[str, Any]:
        from app.services.history_service import get_history_service
        return await get_history_service().get_chart_data_with_fallback(code, range_str)

    def get_benchmark_data(self, symbol: str, days: int = 365) -> Dict:
        cache_key = f"benchmark:{symbol}:{days}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        try:
            import akshare as ak
            df = ak.stock_zh_index_daily(symbol=symbol)
            df['date'] = pd.to_datetime(df['date'])
            if days > 0:
                start_date = datetime.now() - timedelta(days=days)
                df = df[df['date'] >= start_date]
            df = df.sort_values('date')

            if df.empty:
                result = {"dates": [], "values": [], "changes": []}
            else:
                start_value = df['close'].iloc[0]
                df['pct_change'] = ((df['close'] - start_value) / start_value * 100).round(2)
                result = {
                    "symbol": symbol,
                    "dates": df['date'].dt.strftime('%Y-%m-%d').tolist(),
                    "values": [float(v) for v in df['close'].tolist()],
                    "changes": [float(v) for v in df['pct_change'].tolist()],
                    "start_value": float(start_value)
                }
            self.cache.set(cache_key, result, 3600)
            return result
        except Exception as e:
            logger.error(f"获取基准指数失败 {symbol}: {e}")
            return {"dates": [], "values": [], "changes": []}

    def get_compare_data(self, codes: List[str], range_str: str = "1M", include_benchmark: bool = True) -> Dict[str, Any]:
        result = {"funds": [], "benchmarks": [], "range": range_str}
        for code in codes:
            try:
                days = settings.TIME_RANGES.get(range_str, {}).get('days', 90)
                df = self.get_historical_nav(code, days)
                if df.empty:
                    result["funds"].append({"code": code, "name": self.get_fund_name(code), "dates": [], "changes": []})
                    continue
                start_value = df['累计净值'].iloc[0]
                df['pct'] = ((df['累计净值'] - start_value) / start_value * 100).round(2)
                result["funds"].append({
                    "code": code, "name": self.get_fund_name(code),
                    "dates": df['净值日期'].dt.strftime('%Y-%m-%d').tolist(),
                    "changes": [float(v) if pd.notna(v) else None for v in df['pct'].tolist()]
                })
            except Exception as e:
                logger.warning(f"获取对比数据失败 {code}: {e}")
                result["funds"].append({"code": code, "name": self.get_fund_name(code), "dates": [], "changes": []})

        if include_benchmark:
            for bench in [{"name": "上证指数", "symbol": "sh000001"}, {"name": "沪深300", "symbol": "sh000300"}]:
                try:
                    days = settings.TIME_RANGES.get(range_str, {}).get('days', 30)
                    bench_data = self.get_benchmark_data(bench["symbol"], days)
                    result["benchmarks"].append({**bench, **bench_data})
                except Exception as e:
                    logger.warning(f"获取基准数据失败: {e}")
        return result

    def get_compare_data_multi(self, codes: List[str], ranges: List[str], include_benchmark: bool = True) -> Dict:
        data = {}
        for r in ranges:
            try:
                data[r] = self.get_compare_data(codes=codes, range_str=r, include_benchmark=include_benchmark)
            except Exception as e:
                data[r] = {"funds": [], "benchmarks": [], "range": r}
        return {"ranges": data}

    def analyze_trend(self, hist_data: pd.DataFrame, direction: str) -> Tuple[int, float]:
        if hist_data.empty:
            return 0, 0.0
        target = 1 if direction == 'up' else -1
        days = 0
        changes = []
        for i in range(len(hist_data) - 1, 0, -1):
            chg = hist_data.iloc[i]['pct_change']
            if (chg > 0 and target == 1) or (chg < 0 and target == -1):
                days += 1
                changes.append(chg)
            else:
                break
        if days == 0:
            return 0, 0.0
        total_chg = np.prod([1 + r for r in changes]) - 1
        return days, abs(total_chg) if direction == 'up' else -abs(total_chg)

    async def _append_realtime_change(self, hist: pd.DataFrame, code: str) -> pd.DataFrame:
        """将今日实时估值涨跌幅追加到历史数据末尾"""
        try:
            rt = await self.get_realtime_data(code)
            if rt.estimate_change is not None:
                today_chg = float(rt.estimate_change) / 100
                today_row = pd.DataFrame({
                    '净值日期': [datetime.now()],
                    '累计净值': [None],
                    'pct_change': [today_chg]
                })
                hist = pd.concat([hist, today_row], ignore_index=True)
        except Exception:
            pass
        return hist

    async def screen_funds(self, codes: Optional[List[str]] = None, direction: str = 'up',
                     min_days: int = 2, min_pct: float = 0.03,
                     include_realtime: bool = False,
                     batch_size: int = 3, delay_between_batches: float = 1.0) -> List[Dict]:
        if codes is None:
            codes = self._fund_list
        results = []
        for i in range(0, len(codes), batch_size):
            batch = codes[i:i + batch_size]
            for code in batch:
                try:
                    hist = self.get_historical_nav(code, 365)
                    if hist.empty:
                        continue
                    if include_realtime:
                        hist = await self._append_realtime_change(hist, code)
                    days, total_chg = self.analyze_trend(hist, direction)
                    if days >= min_days and abs(total_chg) >= min_pct:
                        results.append({'code': code, 'name': self.get_fund_name(code),
                                       'days': days, 'pct': round(total_chg * 100, 2)})
                except Exception:
                    pass
            if i + batch_size < len(codes):
                await asyncio.sleep(delay_between_batches)
        return sorted(results, key=lambda x: abs(x['pct']), reverse=True)

    async def get_screen_result(self, direction: str = 'up', min_days: Optional[int] = None, min_pct: Optional[float] = None) -> Dict:
        min_days = min_days or (settings.SCREEN_UP["days"] if direction == 'up' else settings.SCREEN_DOWN["days"])
        min_pct = min_pct or (settings.SCREEN_UP["pct"] if direction == 'up' else settings.SCREEN_DOWN["pct"])
        cache_key = f"screen:{direction}:{min_days}:{min_pct}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        results = await self.screen_funds(direction=direction, min_days=min_days, min_pct=min_pct)
        result = {'direction': direction, 'min_days': min_days, 'min_pct': min_pct, 'count': len(results), 'funds': results}
        self.cache.set(cache_key, result, settings.SEARCH_CACHE_TTL)
        return result

    def calculate_period_change(self, hist_data: pd.DataFrame, period_days: int) -> float:
        if hist_data.empty or len(hist_data) < 2:
            return 0.0
        recent = hist_data.tail(period_days + 1)
        if len(recent) < 2:
            return 0.0
        changes = recent['pct_change'].dropna().values
        if len(changes) == 0:
            return 0.0
        total_chg = np.prod([1 + r for r in changes]) - 1
        return total_chg

    async def screen_period(self, codes: Optional[List[str]] = None, direction: str = 'up',
                           period_days: int = 7, min_pct: float = 0.03,
                           include_realtime: bool = False,
                           batch_size: int = 3, delay_between_batches: float = 1.0) -> List[Dict]:
        if codes is None:
            codes = self._fund_list
        results = []
        for i in range(0, len(codes), batch_size):
            batch = codes[i:i + batch_size]
            for code in batch:
                try:
                    hist = self.get_historical_nav(code, 365)
                    if hist.empty:
                        continue
                    if include_realtime:
                        hist = await self._append_realtime_change(hist, code)
                    total_chg = self.calculate_period_change(hist, period_days)
                    if direction == 'up' and total_chg >= min_pct:
                        results.append({'code': code, 'name': self.get_fund_name(code),
                                       'days': period_days, 'pct': round(total_chg * 100, 2)})
                    elif direction == 'down' and total_chg <= -min_pct:
                        results.append({'code': code, 'name': self.get_fund_name(code),
                                       'days': period_days, 'pct': round(total_chg * 100, 2)})
                except Exception:
                    pass
            if i + batch_size < len(codes):
                await asyncio.sleep(delay_between_batches)
        return sorted(results, key=lambda x: abs(x['pct']), reverse=True)

    async def get_period_screen_result(self, direction: str = 'up', period_days: int = 7, min_pct: float = 0.03) -> Dict:
        cache_key = f"period:{direction}:{period_days}:{min_pct}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        results = await self.screen_period(direction=direction, period_days=period_days, min_pct=min_pct)
        result = {'direction': direction, 'period_days': period_days, 'min_pct': min_pct, 'count': len(results), 'funds': results}
        self.cache.set(cache_key, result, settings.SEARCH_CACHE_TTL)
        return result

    def search_funds(self, keyword: str, limit: int = 10) -> List[Dict]:
        cache_key = f"search:{keyword}:{limit}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        results = self._search_from_eastmoney(keyword, limit)
        if results:
            self.cache.set(cache_key, results, settings.SEARCH_CACHE_TTL)
            return results
        try:
            import akshare as ak
            import sys, io
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()
            try:
                df = ak.fund_name_em()
            finally:
                sys.stdout = old_stdout
            if df is not None and not df.empty:
                mask = df['基金简称'].str.contains(keyword, na=False, case=False) | df['基金代码'].str.contains(keyword, na=False)
                matched = df[mask].head(limit)
                results = [{'code': str(r['基金代码']), 'name': str(r['基金简称']), 'type': str(r.get('基金类型', '')), 'company': str(r.get('基金公司', ''))} for _, r in matched.iterrows()]
                if results:
                    self.cache.set(cache_key, results, settings.SEARCH_CACHE_TTL)
                    return results
        except Exception as e:
            logger.debug(f"AKShare搜索失败: {e}")
        return []

    def _search_from_eastmoney(self, keyword: str, limit: int) -> List[Dict]:
        try:
            url = "http://fund.eastmoney.com/js/fundcode_search.js"
            resp = self.session.get(url, timeout=10)
            if resp.status_code != 200:
                return []
            match = re.search(r'var\s+r\s*=\s*(\[.*?\]);', resp.text, re.DOTALL)
            if not match:
                return []
            data = json.loads(match.group(1))
            keyword_lower = keyword.lower()
            matched = []
            for item in data:
                if keyword_lower in item[0].lower() or keyword_lower in item[2].lower():
                    matched.append({'code': item[0], 'name': item[2], 'type': item[3] if len(item) > 3 else '', 'company': ''})
                if len(matched) >= limit:
                    break
            return matched
        except Exception:
            return []

    def get_service_status(self) -> Dict[str, Any]:
        return {
            'fund_count': len(self._fund_list),
            'names_cache_size': len(self._fund_names_cache),
            'cache_stats': self.cache.get_stats()
        }

    def close(self):
        """Clean up resources on shutdown."""
        self.session.close()


_fund_service: Optional[FundService] = None
_fund_service_lock = threading.Lock()


def get_fund_service() -> FundService:
    global _fund_service
    if _fund_service is None:
        with _fund_service_lock:
            if _fund_service is None:
                _fund_service = FundService()
    return _fund_service
