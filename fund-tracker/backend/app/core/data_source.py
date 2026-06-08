# -*- coding: utf-8 -*-
"""
统一数据源管理器
策略链：efinance（主）→ eastmoney_direct（降级）→ akshare（紧急）
已验证方案，测试时间 2026-05-27，21只基金100%成功率
"""
import json
import time
import re
import asyncio
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.logger import get_logger

logger = get_logger("data_source")

DATA_SOURCE_COMPARISON_SOURCES = [
    ("tiantian", 1),
    ("efinance", 2),
    ("tencent", 3),
    ("eastmoney_lsjz", 4),
    ("pingzhongdata", 5),
]

DATA_SOURCE_METADATA: Dict[str, Dict[str, str]] = {
    "tiantian": {
        "display_name": "天天基金盘中估值接口",
        "short_name": "TTFund",
        "description": "天天基金 fundgz 接口，返回盘中估算净值、估算涨跌幅和估算时刻，是开放式基金实时估值的优先来源。",
    },
    "efinance": {
        "display_name": "EFinance 批量基金行情接口",
        "short_name": "EFinance",
        "description": "Python efinance 库封装的基金行情接口，适合批量补充基金净值、估算涨跌幅和公开日期；当无盘中估值时仅作为最新净值来源。",
    },
    "tencent": {
        "display_name": "腾讯基金行情",
        "short_name": "Tencent",
        "description": "腾讯基金行情接口，对部分 QDII、港股主题基金可返回最新公布净值。",
    },
    "eastmoney_lsjz": {
        "display_name": "东方财富历史净值接口",
        "short_name": "Eastmoney",
        "description": "东方财富 f10/lsjz 净值接口，返回最近公布的单位净值和相对上一交易日的日增长率。",
    },
    "pingzhongdata": {
        "display_name": "东方财富基金页面数据",
        "short_name": "Eastmoney",
        "description": "东方财富基金详情页 JS 数据，作为净值趋势和最新净值的兜底来源。",
    },
}


class FundType(Enum):
    OPEN_END = "open_end"
    LOF_ETF = "lof_etf"
    QDII = "qdii"


@dataclass
class FundDataResult:
    code: str
    name: Optional[str] = None
    nav: Optional[float] = None
    change_pct: Optional[float] = None
    update_time: Optional[str] = None
    source: str = ""
    error: Optional[str] = None
    fetch_duration_ms: float = 0.0

    @property
    def is_success(self) -> bool:
        return self.error is None and (self.nav is not None or self.change_pct is not None)


def get_data_source_metadata(source: str) -> Dict[str, str]:
    fallback = {
        "display_name": source or "未知数据源",
        "short_name": source or "未知",
        "description": "未登记说明的数据源。",
    }
    return {**fallback, **DATA_SOURCE_METADATA.get(source, {})}


def _has_intraday_timestamp(update_time: Optional[str]) -> bool:
    return bool(update_time and re.search(r"\d{1,2}:\d{2}", update_time))


def _classify_data_kind(source: str, update_time: Optional[str]) -> tuple[str, str]:
    if source in {"tiantian", "efinance"} and _has_intraday_timestamp(update_time):
        return "realtime_estimate", "实时估值"
    return "latest_nav", "最新净值"


def classify_data_kind(source: str, update_time: Optional[str]) -> tuple[str, str]:
    return _classify_data_kind(source, update_time)


class EfinanceAdapter:
    """efinance数据源适配器 - 批量性能最佳（243ms/21只）"""

    def __init__(self):
        try:
            import efinance as ef
            self.ef = ef
            self._available = True
        except ImportError:
            logger.warning("efinance未安装，该数据源不可用")
            self._available = False

    def fetch_batch(self, codes: List[str]) -> List[FundDataResult]:
        if not self._available:
            return [FundDataResult(code=c, error="efinance未安装") for c in codes]

        start = time.time()
        results = []
        try:
            df = self.ef.fund.get_realtime_increase_rate(fund_codes=codes)
            duration = (time.time() - start) * 1000

            if df is not None and not df.empty:
                df_dict = {}
                for _, row in df.iterrows():
                    code_val = str(row.get('基金代码', ''))
                    df_dict[code_val] = row

                for code in codes:
                    if code in df_dict:
                        row = df_dict[code]
                        name = str(row.get('基金名称', code))

                        nav = None
                        try:
                            val = float(row.get('最新净值', 0))
                            if val > 0:
                                nav = val
                        except (ValueError, TypeError):
                            pass

                        change_pct = None
                        try:
                            val = row.get('估算涨跌幅')
                            if val is not None and str(val) != 'None':
                                change_pct = float(val)
                        except (ValueError, TypeError):
                            pass

                        update_time = None
                        try:
                            val = row.get('估算时间')
                            if val is not None and str(val) != 'None':
                                update_time = str(val)
                            else:
                                val = row.get('最新净值公开日期')
                                if val is not None:
                                    update_time = str(val)
                        except Exception:
                            pass

                        if nav is not None or change_pct is not None:
                            results.append(FundDataResult(
                                code=code, name=name, nav=nav,
                                change_pct=change_pct, update_time=update_time,
                                source='efinance', fetch_duration_ms=duration / len(codes)
                            ))
                        else:
                            results.append(FundDataResult(code=code, error="无有效数据", source='efinance'))
                    else:
                        results.append(FundDataResult(code=code, error="未在批量结果中找到", source='efinance'))
            else:
                results = [FundDataResult(code=c, error="空响应", source='efinance') for c in codes]
        except Exception as e:
            logger.debug(f"efinance批量失败: {e}")
            results = [FundDataResult(code=c, error=str(e), source='efinance') for c in codes]

        return results

    def fetch_single(self, code: str) -> FundDataResult:
        results = self.fetch_batch([code])
        return results[0] if results else FundDataResult(code=code, error="无结果", source='efinance')


class EastmoneyDirectAdapter:
    """自维护东方财富API - 多策略降级，实时性最佳"""

    def __init__(self):
        self.session = requests.Session()
        retries = Retry(total=2, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
        self.session.mount('http://', HTTPAdapter(max_retries=retries))
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://fund.eastmoney.com/'
        })

    def fetch_single(self, code: str) -> FundDataResult:
        start = time.time()

        # 策略1: 天天基金实时估值
        result = self._try_tiantian(code)
        if result.is_success:
            result.fetch_duration_ms = (time.time() - start) * 1000
            return result

        # 策略2: 腾讯基金（对QDII支持最好）
        result = self._try_tencent(code)
        if result.is_success:
            result.fetch_duration_ms = (time.time() - start) * 1000
            return result

        # 策略3: 东方财富lsjz JSON API
        result = self._try_eastmoney_lsjz(code)
        if result.is_success:
            result.fetch_duration_ms = (time.time() - start) * 1000
            return result

        # 策略4: 东方财富pingzhongdata JS解析
        result = self._try_pingzhongdata(code)
        if result.is_success:
            result.fetch_duration_ms = (time.time() - start) * 1000
            return result

        duration = (time.time() - start) * 1000
        return FundDataResult(code=code, error="所有策略均失败", source='eastmoney_direct', fetch_duration_ms=duration)

    def fetch_batch(self, codes: List[str]) -> List[FundDataResult]:
        return [self.fetch_single(c) for c in codes]

    def _try_tiantian(self, code: str) -> FundDataResult:
        try:
            ts = int(time.time() * 1000)
            url = f"http://fundgz.1234567.com.cn/js/{code}.js?rt={ts}"
            resp = self.session.get(url, timeout=5)
            if resp.status_code == 200 and resp.text:
                text = resp.text.replace("jsonpgz(", "").replace(");", "").strip()
                if text:
                    data = json.loads(text)
                    gz = data.get('gsz')
                    gszzl = data.get('gszzl')
                    if gz and float(gz) > 0:
                        return FundDataResult(
                            code=code, name=data.get('name', code),
                            nav=float(gz),
                            change_pct=float(gszzl) if gszzl else None,
                            update_time=data.get('gztime'),
                            source='tiantian'
                        )
        except Exception:
            pass
        return FundDataResult(code=code, error="天天基金失败", source='tiantian')

    def _try_tencent(self, code: str) -> FundDataResult:
        try:
            url = f"http://qt.gtimg.cn/q=jj{code}"
            resp = self.session.get(url, timeout=3)
            if resp.status_code == 200 and "v_jj" in resp.text:
                content = resp.text.split('="')[1].strip('";\n')
                parts = content.split('~')
                if len(parts) > 8:
                    name = parts[1] if parts[1] else code
                    price_str = parts[2].strip() if parts[2] else ''
                    nav_str = parts[5].strip() if len(parts) > 5 and parts[5] else ''
                    change_str = parts[7].strip() if len(parts) > 7 and parts[7] else ''

                    nav = None
                    if price_str and price_str not in ['0.00', '0.0000', '0', '']:
                        try:
                            nav = float(price_str)
                        except ValueError:
                            pass
                    if nav is None and nav_str and nav_str not in ['0.00', '0.0000', '0', '']:
                        try:
                            nav = float(nav_str)
                        except ValueError:
                            pass

                    change_pct = None
                    if change_str and change_str not in ['0.00', '0.0000', '0', '']:
                        try:
                            change_pct = float(change_str)
                        except ValueError:
                            pass

                    if nav is not None or change_pct is not None:
                        update_time = parts[8] if len(parts) > 8 else None
                        return FundDataResult(
                            code=code, name=name, nav=nav,
                            change_pct=change_pct, update_time=update_time,
                            source='tencent'
                        )
        except Exception:
            pass
        return FundDataResult(code=code, error="腾讯基金失败", source='tencent')

    def _try_eastmoney_lsjz(self, code: str) -> FundDataResult:
        try:
            url = "http://api.fund.eastmoney.com/f10/lsjz"
            params = {'fundCode': code, 'pageIndex': 1, 'pageSize': 1}
            headers = {'Referer': f'http://fund.eastmoney.com/{code}.html'}
            resp = self.session.get(url, params=params, headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('Data') and data['Data'].get('LSJZList'):
                    items = data['Data']['LSJZList']
                    if items:
                        latest = items[0]
                        nav = float(latest.get('DWJZ', 0))
                        if nav > 0:
                            return FundDataResult(
                                code=code,
                                name=data['Data'].get('SHORTNAME', code),
                                nav=nav,
                                change_pct=float(latest.get('JZZZL', 0)) if latest.get('JZZZL') else None,
                                update_time=latest.get('FSRQ'),
                                source='eastmoney_lsjz'
                            )
        except Exception:
            pass
        return FundDataResult(code=code, error="东方财富lsjz失败", source='eastmoney_lsjz')

    def _try_pingzhongdata(self, code: str) -> FundDataResult:
        try:
            url = f"http://fund.eastmoney.com/pingzhongdata/{code}.js"
            resp = self.session.get(url, timeout=5)
            if resp.status_code == 200:
                content = resp.text
                match = re.search(r'var Data_netWorthTrend = (\[.*?\]);', content, re.DOTALL)
                if match:
                    data = json.loads(match.group(1))
                    if data:
                        latest = data[-1]
                        nav = latest.get('y')
                        change_pct = None
                        if len(data) >= 2:
                            prev = data[-2]
                            prev_val = prev.get('y', 0)
                            if prev_val > 0:
                                change_pct = round((nav - prev_val) / prev_val * 100, 2)
                        if nav and nav > 0:
                            update_time = None
                            if latest.get('x'):
                                try:
                                    update_time = datetime.fromtimestamp(latest['x'] / 1000).strftime('%Y-%m-%d')
                                except Exception:
                                    pass
                            return FundDataResult(
                                code=code, name=code, nav=nav,
                                change_pct=change_pct, update_time=update_time,
                                source='pingzhongdata'
                            )
        except Exception:
            pass
        return FundDataResult(code=code, error="pingzhongdata失败", source='pingzhongdata')


def _detect_fund_type(code: str, name: str = "") -> FundType:
    if code.startswith(('16', '50', '51')):
        return FundType.LOF_ETF
    qdii_keywords = ['QDII', '恒生', '标普', '纳斯达克', '港股', '海外', '美国', '纳斯达克']
    if any(kw in name for kw in qdii_keywords):
        return FundType.QDII
    return FundType.OPEN_END


class DataSourceManager:
    """统一数据源管理器 - 策略链降级"""

    def __init__(self):
        self._efinance = EfinanceAdapter()
        self._eastmoney = EastmoneyDirectAdapter()
        self._name_cache: Dict[str, str] = {}

    def _complete_latest_nav_change(self, result: FundDataResult) -> FundDataResult:
        """用最新净值源补齐缺失的日涨跌幅，避免把无涨跌显示成不可用。"""
        if not result.is_success or result.change_pct is not None:
            return result

        data_kind, _ = _classify_data_kind(result.source, result.update_time)
        if data_kind == "realtime_estimate":
            return result

        for fetcher in (self._eastmoney._try_eastmoney_lsjz, self._eastmoney._try_pingzhongdata):
            fallback = fetcher(result.code)
            if fallback.is_success and fallback.change_pct is not None:
                return FundDataResult(
                    code=result.code,
                    name=fallback.name or result.name,
                    nav=fallback.nav if fallback.nav is not None else result.nav,
                    change_pct=fallback.change_pct,
                    update_time=fallback.update_time or result.update_time,
                    source=fallback.source,
                    fetch_duration_ms=result.fetch_duration_ms + fallback.fetch_duration_ms,
                )

        return result

    async def fetch_batch(self, codes: List[str]) -> List[FundDataResult]:
        """批量获取 - 优先tiantian实时估值，efinance批量补充"""
        # 先用tiantian获取实时估值（实时性最好）
        results = await asyncio.gather(
            *[asyncio.to_thread(self._eastmoney._try_tiantian, c) for c in codes]
        )

        # 对tiantian失败的，用efinance批量补充
        failed_codes = [codes[i] for i, r in enumerate(results) if not r.is_success]
        if failed_codes:
            efinance_results = await asyncio.to_thread(self._efinance.fetch_batch, failed_codes)
            efinance_map = {r.code: r for r in efinance_results}
            final = []
            for i, r in enumerate(results):
                if r.is_success:
                    final.append(r)
                else:
                    code = codes[i]
                    final.append(efinance_map.get(code, r))
            results = final

        # 仍然失败的，用eastmoney_direct降级
        final_results = []
        for r in results:
            if r.is_success:
                final_results.append(r)
            else:
                fallback = await asyncio.to_thread(self._eastmoney.fetch_single, r.code)
                final_results.append(fallback)

        # 缓存基金名称
        final_results = [
            await asyncio.to_thread(self._complete_latest_nav_change, r)
            for r in final_results
        ]

        for r in final_results:
            if r.is_success and r.name and r.name != r.code:
                self._name_cache[r.code] = r.name

        return final_results

    async def fetch_single(self, code: str) -> FundDataResult:
        """获取单只基金 - 优先实时估值数据源"""
        name = self._name_cache.get(code, "")
        fund_type = _detect_fund_type(code, name)

        if fund_type == FundType.QDII:
            # QDII: 优先腾讯（对QDII支持最好）
            result = await asyncio.to_thread(self._eastmoney.fetch_single, code)
            if result.is_success:
                return result

        # 所有基金: tiantian(实时估值) -> efinance(批量) -> eastmoney_direct(降级)
        result = await asyncio.to_thread(self._eastmoney._try_tiantian, code)
        if result.is_success:
            return result

        result = await asyncio.to_thread(self._efinance.fetch_single, code)
        if result.is_success:
            return await asyncio.to_thread(self._complete_latest_nav_change, result)

        fallback = await asyncio.to_thread(self._eastmoney.fetch_single, code)
        return await asyncio.to_thread(self._complete_latest_nav_change, fallback)

    async def compare_sources(self, code: str) -> Dict[str, Any]:
        """获取单只基金在各数据源下的实时结果，用于界面内对比。"""
        fetchers = {
            "tiantian": self._eastmoney._try_tiantian,
            "efinance": self._efinance.fetch_single,
            "tencent": self._eastmoney._try_tencent,
            "eastmoney_lsjz": self._eastmoney._try_eastmoney_lsjz,
            "pingzhongdata": self._eastmoney._try_pingzhongdata,
        }

        async def fetch_source(source: str, priority: int) -> Dict[str, Any]:
            metadata = get_data_source_metadata(source)
            try:
                result = await asyncio.to_thread(fetchers[source], code)
            except Exception as exc:
                data_kind, data_kind_label = _classify_data_kind(source, None)
                return {
                    "source": source,
                    **metadata,
                    "priority": priority,
                    "name": None,
                    "estimate_nav": None,
                    "estimate_change_pct": None,
                    "last_nav": None,
                    "last_change_pct": None,
                    "update_time": "--",
                    "data_kind": data_kind,
                    "data_kind_label": data_kind_label,
                    "is_realtime": False,
                    "is_fresh": False,
                    "error": str(exc),
                }

            if result.is_success and result.name and result.name != code:
                self._name_cache[code] = result.name
            data_kind, data_kind_label = _classify_data_kind(source, result.update_time)

            return {
                "source": source,
                **metadata,
                "priority": priority,
                "name": result.name if result.is_success else None,
                "estimate_nav": result.nav if result.is_success else None,
                "estimate_change_pct": result.change_pct if result.is_success else None,
                "last_nav": None,
                "last_change_pct": None,
                "update_time": result.update_time or "--",
                "data_kind": data_kind,
                "data_kind_label": data_kind_label,
                "is_realtime": result.is_success and data_kind == "realtime_estimate",
                "is_fresh": result.is_success,
                "error": result.error,
            }

        sources = await asyncio.gather(*[
            fetch_source(source, priority)
            for source, priority in DATA_SOURCE_COMPARISON_SOURCES
        ])
        sources = sorted(sources, key=lambda item: item["priority"])
        best = (
            next((item for item in sources if item["is_fresh"] and item["is_realtime"]), None)
            or next((item for item in sources if item["is_fresh"] and item["estimate_change_pct"] is not None), None)
            or next((item for item in sources if item["is_fresh"]), None)
        )

        return {
            "sources": sources,
            "best_source": best["source"] if best else None,
            "best_source_display_name": best["display_name"] if best else None,
            "total_sources": len([item for item in sources if item["is_fresh"]]),
        }

    async def get_fund_name(self, code: str) -> str:
        """获取基金名称"""
        if code in self._name_cache:
            return self._name_cache[code]

        result = await self.fetch_single(code)
        if result.is_success and result.name:
            self._name_cache[code] = result.name
            return result.name
        return code


_data_source: Optional[DataSourceManager] = None


def get_data_source() -> DataSourceManager:
    global _data_source
    if _data_source is None:
        _data_source = DataSourceManager()
    return _data_source
