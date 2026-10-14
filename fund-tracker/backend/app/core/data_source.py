# -*- coding: utf-8 -*-
"""基金报价：天天优先、新浪估值备用，正式单位净值保持独立口径。"""
import asyncio
import json
import math
import re
import time
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests

from app.config import settings

SHANGHAI = timezone(timedelta(hours=8))
DATA_SOURCE_COMPARISON_SOURCES = [
    ("tiantian", 1), ("sina", 2), ("eastmoney_mobile", 3), ("tencent", 4),
    ("eastmoney_lsjz", 5), ("pingzhongdata", 6),
]
DATA_SOURCE_METADATA = {
    "tiantian": {
        "display_name": "天天基金盘中估值接口", "short_name": "TTFund",
        "description": "天天基金 H5 FundValuationLast 批量接口；部分基金提供盘中估值，未提供估值时保留正式单位净值。",
    },
    "sina": {
        "display_name": "新浪基金估值", "short_name": "新浪",
        "description": "新浪基金页面使用的 fu 行情；估值与涨跌幅读取其页面脚本指定字段，非基金官方净值，估值精度未验证。公开接口无持续可用性或再分发授权保证。",
    },
    "eastmoney_mobile": {
        "display_name": "东方财富移动端单位净值", "short_name": "Eastmoney",
        "description": "FundMNFInfo 批量接口，读取 NAV 单位净值和 PDATE 公布日期；不以 ACCNAV 累计净值计价。与天天基金属于同一上游。",
    },
    "tencent": {
        "display_name": "腾讯基金行情", "short_name": "Tencent",
        "description": "腾讯 jj 基金行情提供最新公布净值，不是场内交易价格或盘中估值。",
    },
    "eastmoney_lsjz": {
        "display_name": "东方财富历史净值接口", "short_name": "Eastmoney",
        "description": "f10/lsjz 的最新单位净值及其净值日期、日增长率。",
    },
    "pingzhongdata": {
        "display_name": "东方财富基金页面数据", "short_name": "Eastmoney",
        "description": "基金页面 Data_netWorthTrend 的最新单位净值；累计净值与单位净值保持区分。",
    },
}


def shanghai_now() -> datetime:
    return datetime.now(SHANGHAI)


def _number(value: Any, positive: bool = False) -> Optional[float]:
    try:
        number = float(value)
        return number if math.isfinite(number) and (not positive or number > 0) else None
    except (ValueError, TypeError):
        return None


def is_current_estimate(update_time: Optional[str], now: Optional[datetime] = None, close_hour: int = 15) -> bool:
    """检查当日、未来时刻和报价延迟；午休、收盘后允许最近交易时段的报价。"""
    if not update_time or not re.search(r"\d{1,2}:\d{2}", update_time):
        return False
    try:
        stamp = datetime.fromisoformat(update_time)
    except ValueError:
        return False
    stamp = stamp.replace(tzinfo=SHANGHAI) if stamp.tzinfo is None else stamp.astimezone(SHANGHAI)
    now = now or shanghai_now()
    now = now.replace(tzinfo=SHANGHAI) if now.tzinfo is None else now.astimezone(SHANGHAI)
    if stamp.date() != now.date() or now.weekday() >= 5 or (stamp - now).total_seconds() > 60:
        return False
    if now.hour < 9 or (now.hour == 9 and now.minute < 30):
        return False
    reference = now
    if (now.hour == 11 and now.minute >= 30) or now.hour == 12:
        reference = now.replace(hour=11, minute=30, second=0, microsecond=0)
    elif now.hour >= close_hour:
        reference = now.replace(hour=close_hour, minute=0, second=0, microsecond=0)
    # 部分跨市场基金在国内收盘后仍更新，接受真实报价时间。
    reference = max(reference, stamp)
    return (reference - stamp).total_seconds() <= settings.ESTIMATE_MAX_AGE_SECONDS


def get_data_source_metadata(source: str) -> Dict[str, str]:
    return {"display_name": source or "未知数据源", "short_name": source or "未知",
            "description": "未登记说明的数据源。", **DATA_SOURCE_METADATA.get(source, {})}


def _classify_data_kind(source: str, update_time: Optional[str]) -> tuple[str, str]:
    if source in {"tiantian", "sina"} and update_time and re.search(r"\d{1,2}:\d{2}", update_time):
        return "realtime_estimate", "实时估值"
    return "latest_nav", "最新净值"


classify_data_kind = _classify_data_kind


def _unit_nav_conflicts(first_nav, first_date, second_nav, second_date) -> bool:
    return bool(first_date and first_date == second_date and first_nav is not None and second_nav is not None
                and abs(first_nav - second_nav) > 0.00015)


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
    data_kind: Optional[str] = None
    previous_nav: Optional[float] = None
    previous_nav_date: Optional[str] = None
    daily_change: Optional[float] = None
    accumulated_nav: Optional[float] = None
    fund_type: Optional[str] = None
    stale_reason: Optional[str] = None
    fetched_at: str = field(default_factory=lambda: shanghai_now().isoformat())

    @property
    def is_success(self) -> bool:
        return self.error is None and _number(self.nav, positive=True) is not None

    @property
    def is_realtime(self) -> bool:
        kind = self.data_kind or _classify_data_kind(self.source, self.update_time)[0]
        return self.is_success and kind == "realtime_estimate" and is_current_estimate(self.update_time)


class EastmoneyDirectAdapter:
    TIANTIAN_URLS = (
        "https://fundcomapi.tiantianfunds.com/mm/newCore/FundValuationLast",
        "https://fundcomapi.eastmoney.com/mm/newCore/FundValuationLast",
    )
    FIELDS = "FCODE,SHORTNAME,FUNDTYPE,GSZZL,GZTIME,GSZ,NAV,PDATE,NAVCHGRT"
    BATCH_SIZE = 100

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                                     "Referer": "https://h5.1234567.com.cn/"})

    def _parse_nav_row(self, row: dict, source: str) -> FundDataResult:
        code = str(row.get("FCODE", "")).strip()
        name = str(row.get("SHORTNAME") or code)
        if row.get("FUNDTYPE") == "005" or "货币" in name:
            return FundDataResult(code=code, name=name, source=source, fund_type="money_market",
                                  error="货币基金需查询万份收益和七日年化，不能把收益字段作为单位净值")
        nav = _number(row.get("NAV"), positive=True)
        date = row.get("PDATE")
        try:
            if not date or datetime.fromisoformat(date).date() > shanghai_now().date():
                nav = None
        except (ValueError, TypeError):
            nav = None
        change = _number(row.get("NAVCHGRT"))
        return FundDataResult(code=code, name=name, nav=nav, change_pct=change,
                              update_time=date, source=source, data_kind="latest_nav",
                              previous_nav=nav, previous_nav_date=date, daily_change=change,
                              accumulated_nav=_number(row.get("ACCNAV"), positive=True),
                              fund_type=str(row.get("FUNDTYPE") or "") or None,
                              error=None if nav is not None and date else "无有效单位净值或净值日期")

    def _parse_tiantian_row(self, row: dict) -> FundDataResult:
        result = self._parse_nav_row(row, "tiantian")
        if result.fund_type == "money_market":
            return result
        estimate = _number(row.get("GSZ"), positive=True)
        estimate_time = row.get("GZTIME")
        if estimate is not None and is_current_estimate(estimate_time):
            result.nav = estimate
            result.change_pct = _number(row.get("GSZZL"))
            result.update_time = estimate_time
            result.data_kind = "realtime_estimate"
            result.error = None
        elif estimate is not None and not is_current_estimate(estimate_time):
            result.stale_reason = f"估值时刻不满足当前时效要求: {estimate_time}"
        return result

    def fetch_tiantian_batch(self, codes: List[str]) -> List[FundDataResult]:
        unique = list(dict.fromkeys(codes))
        result_map = {}
        for offset in range(0, len(unique), self.BATCH_SIZE):
            chunk = unique[offset:offset + self.BATCH_SIZE]
            start = time.perf_counter()
            error = "天天基金批量接口不可用"
            for url in self.TIANTIAN_URLS:
                try:
                    resp = self.session.get(url, params={"FCODES": ",".join(chunk), "FIELDS": self.FIELDS},
                                            timeout=(3, settings.REQUEST_TIMEOUT))
                    resp.raise_for_status()
                    payload = resp.json()
                    if not isinstance(payload, dict) or payload.get("success") is not True or not isinstance(payload.get("data"), list):
                        error = "天天基金业务响应无有效数据数组"
                        continue
                    for row in payload["data"]:
                        if isinstance(row, dict) and str(row.get("FCODE")) in chunk:
                            result = self._parse_tiantian_row(row)
                            result.fetch_duration_ms = (time.perf_counter() - start) * 1000
                            result_map[result.code] = result
                    break  # 缺少某基金估值不意味着服务故障，不重复请求备用域。
                except (requests.RequestException, ValueError, TypeError) as exc:
                    error = f"天天基金批量请求失败: {type(exc).__name__}"
            for code in chunk:
                result_map.setdefault(code, FundDataResult(code=code, source="tiantian", error=error))
        return [result_map[c] for c in codes]

    def _try_tiantian(self, code: str) -> FundDataResult:
        return self.fetch_tiantian_batch([code])[0]

    def fetch_mobile_batch(self, codes: List[str]) -> List[FundDataResult]:
        start = time.perf_counter()
        result_map = {}
        try:
            resp = self.session.get("https://fundmobapi.eastmoney.com/FundMNewApi/FundMNFInfo",
                                    params={"Fcodes": ",".join(codes), "pageIndex": 1, "pageSize": len(codes),
                                            "deviceid": "FundTracker", "plat": "Iphone", "product": "EFund", "version": "6.2.8"},
                                    timeout=(3, settings.REQUEST_TIMEOUT))
            resp.raise_for_status()
            payload = resp.json()
            if isinstance(payload, dict) and payload.get("Success") is True and isinstance(payload.get("Datas"), list):
                for row in payload["Datas"]:
                    if isinstance(row, dict) and str(row.get("FCODE")) in codes:
                        result = self._parse_nav_row(row, "eastmoney_mobile")
                        result.fetch_duration_ms = (time.perf_counter() - start) * 1000
                        result_map[result.code] = result
        except (requests.RequestException, ValueError, TypeError):
            pass
        return [result_map.get(c, FundDataResult(code=c, source="eastmoney_mobile", error="移动端单位净值接口无有效响应")) for c in codes]

    def _try_tencent(self, code: str) -> FundDataResult:
        try:
            resp = self.session.get(f"https://qt.gtimg.cn/q=jj{code}", timeout=settings.REQUEST_TIMEOUT)
            resp.raise_for_status()
            if "v_jj" in resp.text:
                parts = resp.text.split('="', 1)[1].strip('";\n').split('~')
                if len(parts) > 8:
                    name = parts[1] or code
                    if "货币" in name:
                        return FundDataResult(code=code, name=name, source="tencent", fund_type="money_market",
                                              error="货币基金收益不是单位净值")
                    if "货币" not in name:
                        nav = _number(parts[2], positive=True) or _number(parts[5], positive=True)
                        if nav and parts[8]:
                            return FundDataResult(code=code, name=name, nav=nav, change_pct=_number(parts[7]),
                                                  update_time=parts[8], source="tencent", data_kind="latest_nav")
        except (requests.RequestException, ValueError, IndexError):
            pass
        return FundDataResult(code=code, source="tencent", error="腾讯基金无有效单位净值")

    def _try_eastmoney_lsjz(self, code: str) -> FundDataResult:
        try:
            resp = self.session.get("https://api.fund.eastmoney.com/f10/lsjz",
                                    params={"fundCode": code, "pageIndex": 1, "pageSize": 1},
                                    headers={"Referer": f"https://fund.eastmoney.com/{code}.html"},
                                    timeout=settings.REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json().get("Data") or {}
            if data.get("FundType") == "005":
                return FundDataResult(code=code, source="eastmoney_lsjz", fund_type="money_market",
                                      error="货币基金万份收益不是单位净值")
            rows = data.get("LSJZList") or []
            if rows:
                row = rows[0]
                nav = _number(row.get("DWJZ"), positive=True)
                if nav and row.get("FSRQ"):
                    return FundDataResult(code=code, name=data.get("SHORTNAME"), nav=nav,
                                          change_pct=_number(row.get("JZZZL")), update_time=row["FSRQ"],
                                          accumulated_nav=_number(row.get("LJJZ"), positive=True),
                                          source="eastmoney_lsjz", data_kind="latest_nav")
        except (requests.RequestException, ValueError, TypeError):
            pass
        return FundDataResult(code=code, source="eastmoney_lsjz", error="东方财富历史净值接口无有效数据")

    def _try_pingzhongdata(self, code: str) -> FundDataResult:
        try:
            resp = self.session.get(f"https://fund.eastmoney.com/pingzhongdata/{code}.js", timeout=settings.REQUEST_TIMEOUT)
            resp.raise_for_status()
            match = re.search(r'Data_netWorthTrend\s*=\s*(\[.*?\]);', resp.text, re.DOTALL)
            if match:
                rows = json.loads(match.group(1))
                if rows:
                    last = rows[-1]
                    nav = _number(last.get("y"), positive=True)
                    if nav and last.get("x"):
                        stamp = datetime.fromtimestamp(last["x"] / 1000, SHANGHAI).date().isoformat()
                        change = _number(last.get("equityReturn"))
                        return FundDataResult(code=code, nav=nav, change_pct=change, update_time=stamp,
                                              source="pingzhongdata", data_kind="latest_nav")
        except (requests.RequestException, ValueError, TypeError, OverflowError):
            pass
        return FundDataResult(code=code, source="pingzhongdata", error="基金页面无有效单位净值走势")

    def fetch_single(self, code: str) -> FundDataResult:
        for fetcher in (self._try_tencent, self._try_eastmoney_lsjz, self._try_pingzhongdata):
            result = fetcher(code)
            if result.is_success or result.fund_type == "money_market":
                return result
        return FundDataResult(code=code, error="所有正式净值备用接口均失败", source="unknown")


class SinaFundAdapter:
    """新浪自身页面的估值行情，不能把 fu 的末尾另一组数值混作页面估值。"""
    QUOTE_URL = "https://hq.sinajs.cn/list="
    BATCH_SIZE = 100
    # 来源 https://n.sinaimg.cn/finance/fund/quotes/index.js latestValuation。
    ASSIGNMENT = re.compile(r'var\s+hq_str_(f|fu)_(\d{6})\s*=\s*"([^"\r\n]*)"\s*;')

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                                     "Referer": "https://finance.sina.com.cn/"})

    def _parse_quote(self, code: str, estimate: list[str], official: list[str]) -> FundDataResult:
        name = estimate[0] if estimate and estimate[0] else (official[0] if official else code)
        result = FundDataResult(code=code, name=name, source="sina", data_kind="realtime_estimate")
        if "货币" in name:
            result.fund_type = "money_market"
            result.error = "货币基金收益不是单位净值或盘中估值"
            return result
        if len(estimate) < 8:
            result.error = "新浪未提供该基金的盘中估值"
            return result
        stamp = f"{estimate[7]} {estimate[1]}"
        nav = _number(estimate[2], positive=True)
        baseline = _number(estimate[3], positive=True)
        change = _number(estimate[6])
        if nav is None or baseline is None or change is None or change <= -100:
            result.error = "新浪估值或涨跌幅无效"
            return result
        # 四位小数报价允许舍入误差，不接受字段错位、收益冒充价格。
        if abs(nav - baseline * (1 + change / 100)) > 0.00015:
            result.error = "新浪估值与基准单位净值、涨跌幅不一致"
            return result
        if not is_current_estimate(stamp):
            result.error = "新浪估值时刻不满足当前时效要求"
            result.stale_reason = f"估值时刻不满足当前时效要求: {stamp}"
            return result
        result.nav, result.change_pct, result.update_time = nav, change, stamp
        if len(official) >= 5:
            unit_nav = _number(official[1], positive=True)
            try:
                date = datetime.strptime(official[4], "%Y-%m-%d").date()
            except ValueError:
                date = None
            if unit_nav is not None and date is not None and date <= shanghai_now().date():
                result.previous_nav, result.previous_nav_date = unit_nav, date.isoformat()
                result.accumulated_nav = _number(official[2], positive=True)
                # f 行情未给正式日增长率；单位净值比值可能漏掉分红，不冒充该字段。
        return result

    def fetch_batch(self, codes: List[str]) -> List[FundDataResult]:
        unique = list(dict.fromkeys(codes))
        results = {}
        for offset in range(0, len(unique), self.BATCH_SIZE):
            chunk = unique[offset:offset + self.BATCH_SIZE]
            start = time.perf_counter()
            try:
                resp = self.session.get(self.build_quote_url(chunk),
                                        timeout=(3, settings.REQUEST_TIMEOUT))
                resp.raise_for_status()
                resp.encoding = "gb18030"
                results.update({row.code: row for row in self.parse_response(chunk, resp.text)})
            except (requests.RequestException, ValueError, TypeError) as exc:
                for code in chunk:
                    results[code] = FundDataResult(code=code, source="sina", error=f"新浪估值请求失败: {type(exc).__name__}")
            duration = (time.perf_counter() - start) * 1000
            for code in chunk:
                results[code].fetch_duration_ms = duration
        return [results[code] for code in codes]

    def build_quote_url(self, codes: List[str]) -> str:
        # 此服务不解码 %2C，必须像新浪页面一样保留字面逗号。
        return self.QUOTE_URL + ",".join(prefix + code for code in codes for prefix in ("f_", "fu_"))

    def parse_response(self, codes: List[str], body: str) -> List[FundDataResult]:
        # 仅提取精确代码的字符串字段，绝不执行远端 JavaScript。
        fields = {(kind, code): value.split(",") for kind, code, value in self.ASSIGNMENT.findall(body)
                  if code in codes}
        return [self._parse_quote(code, fields.get(("fu", code), []), fields.get(("f", code), [])) for code in codes]


class DataSourceManager:
    def __init__(self):
        self._eastmoney = EastmoneyDirectAdapter()
        self._sina = SinaFundAdapter()
        self._name_cache: Dict[str, str] = {}

    async def fetch_batch(self, codes: List[str]) -> List[FundDataResult]:
        if not codes:
            return []
        unique = list(dict.fromkeys(codes))
        primary = await asyncio.to_thread(self._eastmoney.fetch_tiantian_batch, unique)
        results = {r.code: r for r in primary}
        missing_estimates = [c for c in unique if not results[c].is_realtime and results[c].fund_type != "money_market"]
        if missing_estimates:
            backup = await asyncio.to_thread(self._sina.fetch_batch, missing_estimates)
            for row in backup:
                current = results[row.code]
                if not row.is_realtime:
                    continue  # 估值失败不能丢弃已有的正式单位净值。
                if _unit_nav_conflicts(current.previous_nav, current.previous_nav_date, row.previous_nav, row.previous_nav_date):
                    current.stale_reason = "新浪同日单位净值与天天不一致，未采用其估值"
                    continue
                if (current.previous_nav is not None and current.previous_nav_date
                        and (not row.previous_nav_date or current.previous_nav_date >= row.previous_nav_date)):
                    # 新浪估值和官方净值分别保留，不能覆盖今天已经公布的正式净值。
                    row = replace(row, name=current.name or row.name, previous_nav=current.previous_nav,
                                  previous_nav_date=current.previous_nav_date, daily_change=current.daily_change,
                                  accumulated_nav=current.accumulated_nav or row.accumulated_nav,
                                  fund_type=current.fund_type)
                results[row.code] = row
        pending = [c for c in unique if not results[c].is_success and results[c].fund_type != "money_market"]
        if pending:
            mobile = await asyncio.to_thread(self._eastmoney.fetch_mobile_batch, pending)
            results.update({r.code: r for r in mobile if r.is_success or r.fund_type == "money_market"})
        limiter = asyncio.Semaphore(4)

        async def fallback(code):
            async with limiter:
                return await asyncio.to_thread(self._eastmoney.fetch_single, code)

        pending = [c for c in pending if not results[c].is_success and results[c].fund_type != "money_market"]
        if pending:
            results.update({r.code: r for r in await asyncio.gather(*(fallback(c) for c in pending))})
        for row in results.values():
            if row.is_success and row.name and row.name != row.code:
                self._name_cache[row.code] = row.name
        return [results[c] for c in codes]

    async def fetch_single(self, code: str) -> FundDataResult:
        return (await self.fetch_batch([code]))[0]

    async def compare_sources(self, code: str) -> Dict[str, Any]:
        fetchers = {
            "tiantian": self._eastmoney._try_tiantian,
            "sina": lambda c: self._sina.fetch_batch([c])[0],
            "eastmoney_mobile": lambda c: self._eastmoney.fetch_mobile_batch([c])[0],
            "tencent": self._eastmoney._try_tencent,
            "eastmoney_lsjz": self._eastmoney._try_eastmoney_lsjz,
            "pingzhongdata": self._eastmoney._try_pingzhongdata,
        }

        async def fetch(source, priority):
            start = time.perf_counter()
            try:
                result = await asyncio.to_thread(fetchers[source], code)
            except Exception as exc:
                result = FundDataResult(code=code, source=source, error=type(exc).__name__)
            kind, label = _classify_data_kind(source, result.update_time)
            kind = result.data_kind or kind
            if kind == "latest_nav":
                label = "最新净值"
            elif not result.is_realtime:
                label = "过期估值"
            return {"source": source, **get_data_source_metadata(source), "priority": priority,
                    "name": result.name, "estimate_nav": result.nav if result.is_success else None,
                    "estimate_change_pct": result.change_pct if result.is_success else None,
                    "last_nav": result.previous_nav, "last_nav_date": result.previous_nav_date,
                    "last_change_pct": result.daily_change,
                    "update_time": result.update_time or "--", "data_kind": kind, "data_kind_label": label,
                    "is_available": result.is_success, "is_realtime": result.is_realtime,
                    "is_fresh": result.is_realtime, "error": result.error, "stale_reason": result.stale_reason,
                    "data_timestamp": result.fetched_at,
                    "fetch_duration_ms": round((time.perf_counter() - start) * 1000, 1)}

        sources = await asyncio.gather(*(fetch(s, p) for s, p in DATA_SOURCE_COMPARISON_SOURCES))
        primary = next(s for s in sources if s["source"] == "tiantian")
        for row in sources:
            if row["source"] == "sina" and _unit_nav_conflicts(
                    primary["last_nav"], primary["last_nav_date"], row["last_nav"], row["last_nav_date"]):
                row.update(is_available=False, is_realtime=False, is_fresh=False,
                           estimate_nav=None, estimate_change_pct=None, error="新浪同日单位净值与天天不一致，未采用其估值")
        usable = [s for s in sources if s["is_available"]]
        best = next((s for s in usable if s["is_realtime"]), None)
        if best is None and usable:
            best = max(usable, key=lambda s: (s["update_time"], -s["priority"]))
        return {"sources": sources, "best_source": best["source"] if best else None,
                "best_source_display_name": best["display_name"] if best else None,
                "total_sources": len(usable), "realtime_sources": sum(s["is_realtime"] for s in sources)}

    async def get_fund_name(self, code: str) -> str:
        if code not in self._name_cache:
            result = await self.fetch_single(code)
            if result.name and result.name != code:
                self._name_cache[code] = result.name
        return self._name_cache.get(code, code)

    def close(self):
        self._eastmoney.session.close()
        self._sina.session.close()


_data_source: Optional[DataSourceManager] = None


def get_data_source() -> DataSourceManager:
    global _data_source
    if _data_source is None:
        _data_source = DataSourceManager()
    return _data_source
