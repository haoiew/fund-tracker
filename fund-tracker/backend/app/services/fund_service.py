# -*- coding: utf-8 -*-
"""
基金核心服务 - 统一管理基金数据
合并原FundCoreService + FundDataSourceManager
使用新的DataSourceManager（efinance+eastmoney_direct）和MemoryCache
"""
import asyncio
import html
import json
import time
import os
import re
import threading
from difflib import SequenceMatcher
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
from app.core.data_source import classify_data_kind, get_data_source, get_data_source_metadata, FundDataResult
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
        self._eastmoney_fund_catalog_cache: Optional[List[Dict[str, str]]] = None

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

    def _lookup_catalog_name(self, code: str) -> Optional[str]:
        code = str(code or "").strip()
        if not code:
            return None
        try:
            for item in self._load_eastmoney_fund_catalog():
                if item.get("code") == code and item.get("name"):
                    return item["name"]
        except Exception:
            return None
        return None

    @staticmethod
    def _stock_quote_symbol(raw_code: str) -> Optional[str]:
        code = str(raw_code or "").strip().lower()
        market_match = re.fullmatch(r"(\d+)\.(\d+)", code)
        if market_match:
            market, stock_code = market_match.groups()
            if market == "1":
                return "sh" + stock_code
            if market == "0":
                return "sz" + stock_code
            if market in {"105", "106", "116"}:
                return "hk" + stock_code.zfill(5)
        code = re.sub(r"^(sh|sz|hk|us)", "", code)
        if re.fullmatch(r"\d{6}", code):
            return ("sh" if code.startswith(("5", "6", "9")) else "sz") + code
        if re.fullmatch(r"\d{5}", code):
            return "hk" + code
        if re.fullmatch(r"\d{1,4}", code):
            return "hk" + code.zfill(5)
        if re.fullmatch(r"[a-z.]{1,8}", code):
            return "us" + code.upper()
        return None

    def _fetch_tencent_quote_changes(self, symbols: List[str]) -> Dict[str, float]:
        result: Dict[str, float] = {}
        if not symbols:
            return result
        for chunk_start in range(0, len(symbols), 50):
            chunk = symbols[chunk_start:chunk_start + 50]
            url = "http://qt.gtimg.cn/q=" + ",".join(chunk)
            resp = self.session.get(url, timeout=5)
            if resp.status_code != 200:
                continue
            for line in resp.text.splitlines():
                if "~" not in line:
                    continue
                var_match = re.search(r"v_([^=]+)=", line)
                if not var_match:
                    continue
                symbol = var_match.group(1)
                parts = line.split('="', 1)[-1].strip('";\n').split("~")
                for index in (32, 31, 30, 7):
                    if len(parts) > index:
                        try:
                            value = float(parts[index])
                            if abs(value) < 50:
                                result[symbol] = value
                                break
                        except Exception:
                            continue
        return result

    def _fetch_f10_holding_section(self, code: str, section_type: str) -> str:
        url = "https://fundf10.eastmoney.com/FundArchivesDatas.aspx"
        params = {
            "type": section_type,
            "code": code,
            "topline": "10",
            "year": "",
            "month": "",
            "rt": str(time.time()),
        }
        headers = {"Referer": f"https://fundf10.eastmoney.com/ccmx_{code}.html"}
        resp = self.session.get(url, params=params, headers=headers, timeout=8)
        resp.raise_for_status()
        return html.unescape(resp.text)

    @staticmethod
    def _extract_percent_values(text: str) -> List[float]:
        values: List[float] = []
        for match in re.finditer(r"(-?\d+(?:\.\d+)?)%", text or ""):
            try:
                values.append(float(match.group(1)))
            except ValueError:
                continue
        return values

    def _parse_f10_holding_rows(self, text: str, section_type: str) -> Dict[str, Any]:
        date_match = re.search(r"截止至：<font[^>]*>([^<]+)</font>", text)
        position_date = date_match.group(1).strip() if date_match else None

        holdings = []
        for row_match in re.finditer(r"<tr.*?</tr>", text, re.S):
            row = row_match.group(0)
            cells = [
                re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", cell)).strip()
                for cell in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)
            ]
            if not cells or "序号" in cells[0]:
                continue

            percents = self._extract_percent_values(row)
            if not percents:
                continue

            links = re.findall(r"quote\.eastmoney\.com/unify/r/([^']+)'[^>]*>([^<]+)</a>", row)
            if section_type == "jjcc":
                if links:
                    raw_code, label = links[0]
                    symbol = self._stock_quote_symbol(raw_code) or self._stock_quote_symbol(label)
                    if not symbol:
                        continue
                    code_value = re.sub(r"^(?:\d+\.)", "", raw_code)
                    name = links[1][1] if len(links) > 1 else label
                elif len(cells) >= 3:
                    code_value = cells[1]
                    name = cells[2]
                    symbol = self._stock_quote_symbol(code_value)
                    if not symbol:
                        continue
                else:
                    continue
                holdings.append({
                    "code": code_value,
                    "symbol": symbol,
                    "name": name,
                    "weight": percents[-1],
                    "holding_type": "stock",
                })
            elif section_type == "zqcc" and len(cells) >= 3:
                holdings.append({
                    "code": cells[1],
                    "symbol": "",
                    "name": cells[2],
                    "weight": percents[-1],
                    "holding_type": "bond_or_fund",
                })

        return {"position_date": position_date, "holdings": holdings}

    def _fetch_f10_top_holdings(self, code: str) -> Dict[str, Any]:
        for section_type in ("jjcc", "zqcc"):
            text = self._fetch_f10_holding_section(code, section_type)
            payload = self._parse_f10_holding_rows(text, section_type)
            if payload.get("holdings"):
                payload["source_type"] = section_type
                return payload
        return {"position_date": None, "holdings": [], "source_type": None}

    def _estimate_from_reference_symbols(self, code: str, name: str = "") -> Dict[str, Any]:
        normalized_name = (name or self.get_fund_name(code) or "").lower()
        references: list[dict[str, str]] = []
        if code == "161226" or "白银" in normalized_name:
            references.append({"symbol": "sz161226", "name": "国投白银LOF场内价格", "kind": "exchange_traded_fund"})
        if code in {"007721", "007722"} or "标普500" in normalized_name or "s&p500" in normalized_name:
            references.append({"symbol": "usSPY", "name": "SPDR S&P 500 ETF", "kind": "market_proxy"})

        quote_changes = self._fetch_tencent_quote_changes([item["symbol"] for item in references])
        usable = [
            {**item, "quote_change_pct": quote_changes[item["symbol"]]}
            for item in references
            if item["symbol"] in quote_changes
        ]
        if not usable:
            return {
                "feasible": False,
                "reason": "no_reference_symbol_quote",
                "references": references,
            }

        return {
            "feasible": True,
            "reason": "reference_symbol_quote",
            "reference_count": len(usable),
            "weighted_stock_change_pct": round(sum(item["quote_change_pct"] for item in usable) / len(usable), 4),
            "references": usable,
        }

    def _estimate_from_holdings(self, code: str) -> Dict[str, Any]:
        try:
            payload = self._fetch_f10_top_holdings(code)
        except Exception as exc:
            return {"feasible": False, "reason": f"holdings_source_failed: {exc}"}

        holdings = payload.get("holdings", [])
        if not holdings:
            return {"feasible": False, "reason": "no_parseable_f10_holdings_with_weights"}

        symbol_holdings = [item for item in holdings if item.get("symbol")]
        if not symbol_holdings:
            return {
                "feasible": False,
                "reason": "no_quoteable_symbols_in_f10_holdings",
                "holding_count": len(holdings),
                "position_date": payload.get("position_date"),
                "source_type": payload.get("source_type"),
                "top_holdings": [
                    {
                        "code": item["code"],
                        "name": item["name"],
                        "weight": item["weight"],
                        "holding_type": item.get("holding_type"),
                        "quote_change_pct": None,
                    }
                    for item in holdings[:10]
                ],
            }

        quote_changes = self._fetch_tencent_quote_changes([item["symbol"] for item in symbol_holdings])
        quoted = [item for item in symbol_holdings if item["symbol"] in quote_changes]
        total_weight = sum(float(item["weight"]) for item in holdings)
        quoted_weight = sum(float(item["weight"]) for item in quoted)
        coverage = quoted_weight / total_weight if total_weight else 0
        weighted_change = None
        if quoted_weight:
            weighted_change = sum(float(item["weight"]) * quote_changes[item["symbol"]] for item in quoted) / quoted_weight

        return {
            "feasible": coverage >= 0.6,
            "reason": "ok" if coverage >= 0.6 else "quote_coverage_too_low",
            "holding_count": len(holdings),
            "position_date": payload.get("position_date"),
            "source_type": payload.get("source_type"),
            "quoted_count": len(quoted),
            "quoted_weight_coverage": round(coverage, 4),
            "weighted_stock_change_pct": round(weighted_change, 4) if weighted_change is not None else None,
            "top_holdings": [
                {
                    "code": item["code"],
                    "name": item["name"],
                    "weight": item["weight"],
                    "holding_type": item.get("holding_type"),
                    "quote_change_pct": quote_changes.get(item["symbol"]),
                }
                for item in holdings[:10]
            ],
        }

    def _build_fallback_estimate(self, direct: FundRealtimeData, exchange_or_quote_sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        source = None
        reason = "no_usable_latest_nav_or_quote_change"
        change_pct = None
        update_time = direct.update_time

        quote_source = next(
            (
                item for item in exchange_or_quote_sources
                if item.get("change_pct") is not None and item.get("source") == "tencent"
            ),
            None,
        )
        if quote_source:
            source = "tencent"
            reason = "quote_source_change_pct"
            change_pct = quote_source.get("change_pct")
            update_time = quote_source.get("update_time") or update_time
        elif direct.estimate_change is not None:
            source = direct.data_source
            reason = "latest_nav_change_pct"
            change_pct = float(direct.estimate_change)

        feasible = change_pct is not None
        return {
            "feasible": feasible,
            "reason": reason if feasible else "no_usable_latest_nav_or_quote_change",
            "source": source,
            "change_pct": change_pct,
            "update_time": update_time,
            "data_kind": direct.data_kind,
            "is_realtime": direct.is_realtime,
        }

    def _build_realtime_response(self, code: str, name: str, result: FundDataResult) -> FundRealtimeData:
        source = result.source or "unknown"
        metadata = get_data_source_metadata(source)
        data_kind, data_kind_label = classify_data_kind(source, result.update_time)
        is_realtime = result.is_success and data_kind == "realtime_estimate"

        if result.is_success:
            resolved_name = result.name or name
            if not resolved_name or resolved_name == code:
                resolved_name = self._lookup_catalog_name(code) or resolved_name or code
            status = "正常" if is_realtime else data_kind_label
            rt = FundRealtimeData(
                code=code,
                name=resolved_name,
                estimate_nav=Decimal(str(result.nav)) if result.nav else None,
                estimate_change=Decimal(str(result.change_pct)) if result.change_pct is not None else None,
                update_time=result.update_time or '--',
                status=status,
                data_source=source,
                data_source_display_name=metadata.get("display_name"),
                data_source_short_name=metadata.get("short_name"),
                data_source_description=metadata.get("description"),
                data_kind=data_kind,
                data_kind_label=data_kind_label,
                is_realtime=is_realtime,
            )
            if resolved_name and resolved_name != code:
                self._fund_names_cache[code] = resolved_name
                self.cache.set(f"fund_name:{code}", resolved_name, settings.FUND_INFO_CACHE_TTL)
            return rt

        return FundRealtimeData(
            code=code, name=name,
            status='获取失败',
            data_source=source,
            data_source_display_name=metadata.get("display_name"),
            data_source_short_name=metadata.get("short_name"),
            data_source_description=metadata.get("description"),
            data_kind=data_kind,
            data_kind_label=data_kind_label,
            is_realtime=False,
        )

    async def get_realtime_data(self, code: str) -> FundRealtimeData:
        """获取单只基金实时数据"""
        cache_key = f"realtime:{code}"
        cached = self.cache.get(cache_key)
        if cached and isinstance(cached, FundRealtimeData):
            return cached

        name = self.get_fund_name(code)
        result = await self._data_source.fetch_single(code)
        rt = self._build_realtime_response(code, name, result)

        self.cache.set(cache_key, rt, settings.REALTIME_CACHE_TTL)
        return rt

    async def get_data_source_comparison(self, code: str, name: Optional[str] = None) -> Dict[str, Any]:
        """获取单只基金各数据源的实时估值对比。"""
        comparison = await self._data_source.compare_sources(code)
        resolved_name = (
            name
            or next((item.get("name") for item in comparison["sources"] if item.get("name")), None)
            or self._fund_names_cache.get(code)
            or self.get_fund_name(code)
        )

        return {
            "code": code,
            "name": resolved_name or code,
            "sources": comparison["sources"],
            "best_source": comparison["best_source"],
            "best_source_display_name": comparison.get("best_source_display_name"),
            "total_sources": comparison["total_sources"],
        }

    async def get_realtime_alternatives(self, code: str, name: Optional[str] = None) -> Dict[str, Any]:
        """获取缺失真实实时估值时的替代方案。"""
        direct = await self.get_realtime_data(code)
        if direct.is_realtime:
            return {
                "code": code,
                "name": direct.name,
                "direct": {
                    "change_pct": float(direct.estimate_change) if direct.estimate_change is not None else None,
                    "update_time": direct.update_time,
                    "source": direct.data_source,
                    "data_kind": direct.data_kind,
                    "is_realtime": direct.is_realtime,
                },
                "skipped": True,
                "reason": "direct_realtime_available",
                "same_name_realtime_candidates": [],
                "exchange_or_quote_sources": [],
                "holdings_based_estimate": None,
            }

        search_keyword = name or direct.name or code
        candidates = self.search_funds(search_keyword, 8)
        candidate_codes = [item["code"] for item in candidates if item.get("code") and item["code"] != code]
        same_name_realtime_candidates = []
        if candidate_codes:
            rows = await self.get_realtime_batch(candidate_codes)
            same_name_realtime_candidates = [
                {
                    "code": row.code,
                    "name": row.name,
                    "change_pct": float(row.estimate_change) if row.estimate_change is not None else None,
                    "update_time": row.update_time,
                    "source": row.data_source,
                    "is_realtime": row.is_realtime,
                }
                for row in rows
                if row.is_realtime
            ]

        comparison = await self.get_data_source_comparison(code, name)
        exchange_or_quote_sources = [
            {
                "source": item["source"],
                "display_name": item.get("display_name"),
                "change_pct": item.get("estimate_change_pct"),
                "update_time": item.get("update_time"),
                "is_realtime": item.get("is_realtime"),
            }
            for item in comparison["sources"]
            if item["source"] in {"tencent", "tiantian"} and item.get("is_fresh")
        ]
        holdings_estimate = await asyncio.to_thread(self._estimate_from_holdings, code)
        reference_estimate = await asyncio.to_thread(self._estimate_from_reference_symbols, code, direct.name)
        fallback_estimate = self._build_fallback_estimate(direct, exchange_or_quote_sources)

        return {
            "code": code,
            "name": direct.name,
            "direct": {
                "change_pct": float(direct.estimate_change) if direct.estimate_change is not None else None,
                "update_time": direct.update_time,
                "source": direct.data_source,
                "data_kind": direct.data_kind,
                "is_realtime": direct.is_realtime,
            },
            "skipped": False,
            "reason": "direct_realtime_unavailable",
            "same_name_realtime_candidates": same_name_realtime_candidates,
            "exchange_or_quote_sources": exchange_or_quote_sources,
            "holdings_based_estimate": holdings_estimate,
            "reference_symbol_estimate": reference_estimate,
            "fallback_estimate": fallback_estimate,
        }

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
                rt = self._build_realtime_response(code, name, result)
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

    def calculate_period_change(self, hist_data: pd.DataFrame, period_days: int, calendar_days: bool = False) -> float:
        if hist_data.empty or len(hist_data) < 2:
            return 0.0

        if calendar_days:
            # 自然日模式：从当前日期往前推 N 天，找到对应的数据
            cutoff_date = datetime.now() - timedelta(days=period_days)
            hist_data_copy = hist_data.copy()
            if '净值日期' in hist_data_copy.columns:
                hist_data_copy['净值日期'] = pd.to_datetime(hist_data_copy['净值日期'])
                recent = hist_data_copy[hist_data_copy['净值日期'] >= cutoff_date]
            else:
                recent = hist_data.tail(period_days + 1)
        else:
            # 交易日模式：取最近 N 条记录
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
                           include_realtime: bool = False, calendar_days: bool = False,
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
                    total_chg = self.calculate_period_change(hist, period_days, calendar_days)
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
        keyword = str(keyword or "").strip()
        if not keyword:
            return []
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
                mask = (
                    df['基金简称'].str.contains(keyword, na=False, case=False, regex=False)
                    | df['基金代码'].astype(str).str.contains(keyword, na=False, regex=False)
                )
                matched = df[mask].head(limit)
                results = [{'code': str(r['基金代码']), 'name': str(r['基金简称']), 'type': str(r.get('基金类型', '')), 'company': str(r.get('基金公司', ''))} for _, r in matched.iterrows()]
                if results:
                    self.cache.set(cache_key, results, settings.SEARCH_CACHE_TTL)
                    return results
        except Exception as e:
            logger.debug(f"AKShare搜索失败: {e}")
        return []

    @staticmethod
    def _normalize_search_text(value: str) -> str:
        text = re.sub(r"[\s（）()【】\[\]·,，.。_-]+", "", str(value or "").lower())
        for word in ("证券投资基金", "开放式", "基金", "混合型", "股票型", "债券型", "指数型", "发起式", "发起"):
            text = text.replace(word, "")
        text = re.sub(r"(东方红中证)东方红", r"\1", text)
        text = text.replace("东方红红利", "东方红中证红利")
        return text

    @staticmethod
    def _is_ordered_subsequence(needle: str, haystack: str) -> bool:
        if not needle:
            return False
        position = 0
        for char in haystack:
            if position < len(needle) and needle[position] == char:
                position += 1
        return position == len(needle)

    def _score_search_match(self, keyword: str, item: Dict[str, str]) -> int:
        code = str(item.get('code', ''))
        name = str(item.get('name', ''))
        keyword_lower = keyword.lower()
        normalized_keyword = self._normalize_search_text(keyword)
        normalized_name = self._normalize_search_text(name)
        if keyword_lower == code.lower():
            return 120
        if keyword_lower and keyword_lower in code.lower():
            return 110
        if keyword_lower and keyword_lower in name.lower():
            return 100
        if normalized_keyword and normalized_keyword == normalized_name:
            return 98
        if normalized_keyword and normalized_keyword in normalized_name:
            return 94
        if len(normalized_keyword) >= 4 and self._is_ordered_subsequence(normalized_keyword, normalized_name):
            return 86
        if len(normalized_keyword) >= 4:
            ratio = SequenceMatcher(None, normalized_keyword, normalized_name).ratio()
            return int(ratio * 80)
        return 0

    def _load_eastmoney_fund_catalog(self) -> List[Dict[str, str]]:
        if self._eastmoney_fund_catalog_cache is not None:
            return self._eastmoney_fund_catalog_cache
        try:
            url = "http://fund.eastmoney.com/js/fundcode_search.js"
            resp = self.session.get(url, timeout=10)
            if resp.status_code != 200:
                self._eastmoney_fund_catalog_cache = []
                return []
            match = re.search(r'var\s+r\s*=\s*(\[.*?\]);', resp.text, re.DOTALL)
            if not match:
                self._eastmoney_fund_catalog_cache = []
                return []
            data = json.loads(match.group(1))
            self._eastmoney_fund_catalog_cache = [
                {
                    'code': str(item[0]),
                    'name': str(item[2]),
                    'type': str(item[3]) if len(item) > 3 else '',
                    'company': ''
                }
                for item in data
                if len(item) >= 3
            ]
            return self._eastmoney_fund_catalog_cache
        except Exception:
            self._eastmoney_fund_catalog_cache = []
            return []

    def _search_from_eastmoney(self, keyword: str, limit: int) -> List[Dict]:
        try:
            data = self._load_eastmoney_fund_catalog()
            matched = []
            for item in data:
                score = self._score_search_match(keyword, item)
                if score >= 70:
                    matched.append({**item, '_score': score})
            matched.sort(key=lambda item: item.get('_score', 0), reverse=True)
            return [{key: value for key, value in item.items() if key != '_score'} for item in matched[:limit]]
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
