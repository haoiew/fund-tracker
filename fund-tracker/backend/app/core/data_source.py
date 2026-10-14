# -*- coding: utf-8 -*-
"""Provider HTTP collection and shared snapshots; normalization/contract live separately."""
import asyncio
import re
import time
from collections import OrderedDict
from dataclasses import asdict, replace
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests

from app.config import settings
from app.core.cache import get_cache
from app.core import data_contract as contract
from app.core import provider_normalizers as normalizers
# Re-export the established interface for existing services and diagnostics.
from app.core.data_contract import (
    FundDataResult, SHANGHAI, ESTIMATE_SOURCES, NAV_SOURCES, DATA_SOURCE_COMPARISON_SOURCES,
    DATA_SOURCE_METADATA, PROVIDER_SPECS, _number, _classify_data_kind, _unit_nav_conflicts,
    classify_data_kind, describe_quote_quality, get_data_source_metadata,
    is_current_estimate,
)


def shanghai_now():
    return contract.shanghai_now()


class EastmoneyDirectAdapter:
    TIANTIAN_URL = "https://fundcomapi.tiantianfunds.com/mm/newCore/FundValuationLast"
    FIELDS = "FCODE,SHORTNAME,FUNDTYPE,GSZZL,GZTIME,GSZ,NAV,PDATE,NAVCHGRT"
    BATCH_SIZE = 100

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                                     "Referer": "https://h5.1234567.com.cn/"})

    def _parse_nav_row(self, row: dict, source: str) -> FundDataResult:
        return normalizers.normalize_eastmoney_nav(row, source)

    def _parse_tiantian_row(self, row: dict) -> FundDataResult:
        return normalizers.normalize_tiantian(row)

    def fetch_tiantian_batch(self, codes: List[str]) -> List[FundDataResult]:
        unique = list(dict.fromkeys(codes))
        result_map = {}
        for offset in range(0, len(unique), self.BATCH_SIZE):
            chunk = unique[offset:offset + self.BATCH_SIZE]
            start = time.perf_counter()
            error = "天天基金批量接口不可用"
            try:
                resp = self.session.post(self.TIANTIAN_URL, data={"FCODES": ",".join(chunk), "FIELDS": self.FIELDS},
                                         timeout=(3, settings.REQUEST_TIMEOUT))
                resp.raise_for_status()
                payload = resp.json()
                if not isinstance(payload, dict) or payload.get("success") is not True or not isinstance(payload.get("data"), list):
                    error = "天天基金业务响应无有效数据数组"
                else:
                    for row in payload["data"]:
                        if isinstance(row, dict) and str(row.get("FCODE")) in chunk:
                            result = self._parse_tiantian_row(row)
                            result.fetch_duration_ms = (time.perf_counter() - start) * 1000
                            result_map[result.code] = result
            except (requests.RequestException, ValueError, TypeError) as exc:
                error = f"天天基金批量请求失败: {type(exc).__name__}"
            for code in chunk:
                result_map.setdefault(code, FundDataResult(code=code, source="tiantian", error=error))
        return [result_map[c] for c in codes]

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
            return normalizers.normalize_tencent(code, resp.text)
        except (requests.RequestException, ValueError, IndexError):
            return FundDataResult(code=code, source="tencent", error="腾讯基金无有效单位净值")

    def _try_eastmoney_lsjz(self, code: str) -> FundDataResult:
        try:
            resp = self.session.get("https://api.fund.eastmoney.com/f10/lsjz",
                                    params={"fundCode": code, "pageIndex": 1, "pageSize": 1},
                                    headers={"Referer": f"https://fund.eastmoney.com/{code}.html"},
                                    timeout=settings.REQUEST_TIMEOUT)
            resp.raise_for_status()
            return normalizers.normalize_lsjz(code, resp.json())
        except (requests.RequestException, ValueError, TypeError):
            return FundDataResult(code=code, source="eastmoney_lsjz", error="东方财富历史净值接口无有效数据")

    def _try_pingzhongdata(self, code: str) -> FundDataResult:
        try:
            resp = self.session.get(f"https://fund.eastmoney.com/pingzhongdata/{code}.js", timeout=settings.REQUEST_TIMEOUT)
            resp.raise_for_status()
            return normalizers.normalize_pingzhongdata(code, resp.text)
        except (requests.RequestException, ValueError, TypeError, OverflowError):
            return FundDataResult(code=code, source="pingzhongdata", error="基金页面无有效单位净值走势")

class SinaFundAdapter:
    """新浪自身页面的估值行情，不能把 fu 的末尾另一组数值混作页面估值。"""
    QUOTE_URL = "https://hq.sinajs.cn/list="
    BATCH_SIZE = 100
    # 来源 https://n.sinaimg.cn/finance/fund/quotes/index.js latestValuation。
    ASSIGNMENT = normalizers.SINA_ASSIGNMENT

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                                     "Referer": "https://finance.sina.com.cn/"})

    def _parse_quote(self, code: str, estimate: list[str], official: list[str]) -> FundDataResult:
        return normalizers.normalize_sina_quote(code, estimate, official)

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
        return normalizers.normalize_sina(codes, body)




class DayfundAdapter:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0"

    @staticmethod
    def parse_response(code: str, body: str) -> FundDataResult:
        return normalizers.normalize_dayfund(code, body)

    def fetch_single(self, code: str) -> FundDataResult:
        response = self.session.get("https://fund.dayfund.com.cn/ajs/ajaxdata.shtml",
                                    params={"showtype": "getfundvalue", "fundcode": code},
                                    headers={"Referer": f"https://fund.dayfund.com.cn/fundpre/{code}.html"},
                                    timeout=(3, settings.REQUEST_TIMEOUT))
        response.raise_for_status()
        response.encoding = "utf-8"
        return self.parse_response(code, response.text)

    def close(self):
        self.session.close()


class Fund123Adapter:
    """仅使用正常匿名页面流程；Cookie/CSRF 仅存内存，异常不暴露请求 URL。"""
    def __init__(self):
        self._contexts = OrderedDict()

    def _context(self, code: str):
        cached = self._contexts.pop(code, None)
        if cached and time.monotonic() < cached[0]:
            self._contexts[code] = cached
            return cached[1:]
        if cached:
            cached[1].close()
        session = requests.Session()
        url = f"https://www.fund123.cn/matiaria?fundCode={code}"
        session.headers.update({"User-Agent": "Mozilla/5.0", "Referer": url})
        try:
            response = session.get(url, timeout=(3, settings.REQUEST_TIMEOUT))
            response.raise_for_status()
            response.encoding = "utf-8"
            fields = {}
            for field_name in ("csrf", "productId", "netValue"):
                match = re.search(r'"' + field_name + r'":"([^"\r\n]+)"', response.text)
                if not match:
                    raise ValueError("数米匿名页面缺少必要字段")
                fields[field_name] = match.group(1)
            name = re.search(r'"fundName":"([^"\r\n]+)"', response.text)
            fields["name"] = name.group(1) if name else code
            self._contexts[code] = (time.monotonic() + 600, session, fields)
            while len(self._contexts) > 200:
                _, expired = self._contexts.popitem(last=False)
                expired[1].close()
            return session, fields
        except Exception:
            session.close()
            raise

    @staticmethod
    def parse_response(code: str, payload, baseline=None, name=None) -> FundDataResult:
        return normalizers.normalize_fund123(code, payload, baseline, name)

    def fetch_single(self, code: str) -> FundDataResult:
        try:
            session, fields = self._context(code)
            now = shanghai_now()
            response = session.post("https://www.fund123.cn/api/fund/queryFundEstimateIntraday",
                                    params={"_csrf": fields["csrf"]},
                                    json={"startTime": now.date().isoformat(),
                                          "endTime": (now + timedelta(days=1)).date().isoformat(), "limit": 200,
                                          "productId": fields["productId"], "format": True, "source": "WEALTHBFFWEB"},
                                    timeout=(3, settings.REQUEST_TIMEOUT))
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or payload.get("success") is not True:
                raise ValueError("数米估值业务响应失败")
            return self.parse_response(code, payload, fields["netValue"], fields["name"])
        except (requests.RequestException, ValueError, TypeError, KeyError) as exc:
            cached = self._contexts.pop(code, None)
            if cached:
                cached[1].close()
            return FundDataResult(code=code, source="fund123", error=f"数米估值请求失败: {type(exc).__name__}")

    def close(self):
        for _, session, _ in self._contexts.values():
            session.close()
        self._contexts.clear()


class DataSourceManager:
    def __init__(self):
        self._eastmoney = EastmoneyDirectAdapter()
        self._sina = SinaFundAdapter()
        self._dayfund = DayfundAdapter()
        self._fund123 = Fund123Adapter()
        self._cache = get_cache()
        self._pending = {}
        self._ready = {}
        self._name_cache: Dict[str, str] = {}

    async def _fetch_source_batch(self, source: str, codes: List[str], on_results=None) -> List[FundDataResult]:
        fetchers = {
            "sina": self._sina.fetch_batch, "tiantian": self._eastmoney.fetch_tiantian_batch,
            "eastmoney_mobile": self._eastmoney.fetch_mobile_batch,
            "dayfund": self._dayfund.fetch_single, "fund123": self._fund123.fetch_single,
            "tencent": self._eastmoney._try_tencent,
            "eastmoney_lsjz": self._eastmoney._try_eastmoney_lsjz,
            "pingzhongdata": self._eastmoney._try_pingzhongdata,
        }
        # 各站独立限并发，不能让某个低优先级站点占满线程池而阻塞新浪批量请求。
        limiter = asyncio.Semaphore(settings.SOURCE_SINGLE_CONCURRENCY)

        async def call(fetcher, requested):
            start = time.perf_counter()
            started_at = shanghai_now().isoformat()
            try:
                rows = await asyncio.to_thread(fetcher, requested)
                rows = rows if isinstance(requested, list) else [rows]
            except Exception as exc:
                # 请求异常可能含 CSRF URL，不把异常全文写入日志或 API。
                codes_failed = requested if isinstance(requested, list) else [requested]
                rows = [FundDataResult(code=code, source=source, error=f"请求失败: {type(exc).__name__}") for code in codes_failed]
            duration = (time.perf_counter() - start) * 1000
            results = [replace(row, source=source, fetch_duration_ms=duration, fetch_started_at=started_at) for row in rows]
            if on_results:
                on_results(results)
            return results

        async def one(code):
            async with limiter:
                return (await call(fetchers[source], code))[0]

        tasks = ([asyncio.create_task(call(fetchers[source], codes))] if PROVIDER_SPECS[source].supports_batch
                 else [asyncio.create_task(one(code)) for code in codes])
        try:
            done, pending = await asyncio.wait(tasks, timeout=settings.SOURCE_BATCH_TIMEOUT)
            results = {}
            for task in done:
                rows = task.result()
                for row in rows if isinstance(rows, list) else [rows]:
                    results[row.code] = row
            return [results.get(code, FundDataResult(code=code, source=source, error="该源本轮采集超时")) for code in codes]
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    @staticmethod
    def _normalize_snapshot(code, source_results):
        results = dict(source_results)
        name = next((results[source].name for source in ("tiantian", "sina", *NAV_SOURCES)
                     if source in results and results[source].name and results[source].name != code), None)
        for source, row in results.items():
            if row.previous_nav is not None and row.previous_nav_date and not row.previous_nav_source:
                row = replace(row, previous_nav_source=source)
                results[source] = row
            if name and (not row.name or row.name == code):
                row = replace(row, name=name)
                results[source] = row
            if row.is_success and (row.data_kind or _classify_data_kind(source, row.update_time)[0]) == "latest_nav":
                try:
                    date = datetime.strptime(row.update_time, "%Y-%m-%d").date()
                    valid = date <= shanghai_now().date()
                except (ValueError, TypeError):
                    valid = False
                results[source] = (replace(row, previous_nav=row.nav, previous_nav_date=date.isoformat(), previous_nav_source=source,
                                           daily_change=row.daily_change if row.daily_change is not None else row.change_pct) if valid
                                   else replace(row, error="无有效正式净值日期"))
        # 正式净值校核不随估值优先级改变；天天/移动端同日单位净值用于识别字段错位。
        authority = next((results[source] for source in ("tiantian", "eastmoney_mobile")
                          if source in results and results[source].previous_nav is not None
                          and results[source].previous_nav_date), None)
        if authority:
            for source, row in results.items():
                if source in ESTIMATE_SOURCES and source != authority.source and _unit_nav_conflicts(
                        authority.previous_nav, authority.previous_nav_date, row.previous_nav, row.previous_nav_date):
                    reason = "同日单位净值与正式净值接口不一致，未采用其估值"
                    results[source] = replace(row, error=reason, stale_reason=reason)
        # 新浪等接口即使缺估值，也可能独立给出有效正式净值；保留但绝不标作实时估值。
        for source, row in results.items():
            if (row.error and row.fund_type != "money_market" and row.previous_nav is not None
                    and row.previous_nav_date and not (row.stale_reason and "不一致" in row.stale_reason)):
                results[source] = replace(row, nav=row.previous_nav, change_pct=row.daily_change,
                                           update_time=row.previous_nav_date, data_kind="latest_nav", error=None,
                                           stale_reason=row.stale_reason or row.error)
        return results

    async def _collect_sources(self, codes, ready):
        # 占位只表示尚未返回，不能伪装为请求失败或有效报价。
        raw = {code: {source: FundDataResult(code=code, source=source, is_pending=True)
                      for source, _ in DATA_SOURCE_COMPARISON_SOURCES} for code in codes}

        for code, snapshot in raw.items():
            self._cache.set(f"source_snapshot:{code}", snapshot, settings.REALTIME_CACHE_TTL)

        def publish(source, rows):
            for row in rows:
                if row.code not in raw:
                    continue
                raw[row.code][source] = replace(row, is_pending=False)
                snapshot = self._normalize_snapshot(row.code, raw[row.code])
                self._cache.set(f"source_snapshot:{row.code}", snapshot, settings.REALTIME_CACHE_TTL)
            ready.set()

        async def collect(source):
            rows = await self._fetch_source_batch(source, codes, lambda rows: publish(source, rows))
            publish(source, rows)  # 包括本源预算超时/未返回的代码，明确完成状态。

        try:
            await asyncio.gather(*(collect(source) for source, _ in DATA_SOURCE_COMPARISON_SOURCES))
        finally:
            ready.set()

    async def _get_snapshots(self, codes, refresh=False, wait_all=True):
        missing, tasks = [], {}
        loop = asyncio.get_running_loop()
        for code in dict.fromkeys(codes):
            task = self._pending.get((loop, code))
            if task is not None:
                tasks[task] = self._ready[task]
            elif refresh or self._cache.get(f"source_snapshot:{code}") is None:
                missing.append(code)
        if missing:
            ready = asyncio.Event()
            task = asyncio.create_task(self._collect_sources(missing, ready))
            self._ready[task] = ready
            for code in missing:
                self._pending[(loop, code)] = task

            def finished(completed):
                ready.set()
                self._ready.pop(completed, None)
                for code in missing:
                    self._pending.pop((loop, code), None)
                if not completed.cancelled():
                    completed.exception()

            task.add_done_callback(finished)
            tasks[task] = ready
        if wait_all:
            await asyncio.gather(*(asyncio.shield(task) for task in tasks))
        else:
            # 首个已返回结果即可读取，后续轮询只读同一采集任务的快照。
            await asyncio.gather(*(asyncio.shield(ready.wait()) for ready in tasks.values()))
            for task in tasks:
                if task.done() and not task.cancelled():
                    task.result()
        return {code: self._cache.get(f"source_snapshot:{code}") for code in dict.fromkeys(codes)}

    async def wait_for_pending(self):
        """关机/完整诊断时收尾后台采集；普通界面不等待此方法。"""
        loop = asyncio.get_running_loop()
        tasks = {task for (owner, _), task in self._pending.items() if owner is loop}
        if tasks:
            await asyncio.gather(*(asyncio.shield(task) for task in tasks))

    @staticmethod
    def _select_result(code, snapshot):
        ordered = [snapshot[source] for source, _ in DATA_SOURCE_COMPARISON_SOURCES]
        pending = [row.source for row in ordered if row.is_pending]
        progress = {"pending_sources": pending, "primary_source_complete": not snapshot.get("sina", FundDataResult(code=code)).is_pending}
        money = next((row for row in ordered if row.fund_type == "money_market"), None)
        if money:
            return replace(money, **progress)
        # 优先级仅决定实时估值；正式净值先比净值日，再比正式源顺序。
        nav_order = ("tiantian", "eastmoney_mobile", "eastmoney_lsjz", "pingzhongdata", "tencent", "sina", "dayfund", "fund123")
        navs = [snapshot[source] for source in nav_order if source in snapshot
                and snapshot[source].previous_nav is not None and snapshot[source].previous_nav_date
                and not (snapshot[source].stale_reason and "不一致" in snapshot[source].stale_reason)]
        official = max(navs, key=lambda row: row.previous_nav_date) if navs else None
        selected = next((row for row in ordered if row.is_realtime), None)
        if selected:
            if official:
                selected = replace(selected, previous_nav=official.previous_nav, previous_nav_date=official.previous_nav_date,
                                   previous_nav_source=official.previous_nav_source or official.source,
                                   daily_change=official.daily_change, accumulated_nav=official.accumulated_nav,
                                   name=selected.name if selected.name and selected.name != code else official.name,
                                   fund_type=official.fund_type or selected.fund_type)
            return replace(selected, **progress)
        if official:
            reason = next((row.stale_reason for row in ordered if row.stale_reason), None)
            return replace(official, nav=official.previous_nav, change_pct=official.daily_change,
                           update_time=official.previous_nav_date, data_kind="latest_nav", error=None, stale_reason=reason, **progress)
        return FundDataResult(code=code, source="unknown", data_kind="unavailable",
                              error=None if pending else "所有数据源均无有效估值或正式净值", **progress)

    async def fetch_batch(self, codes: List[str], refresh: bool = False, wait_all: bool = True) -> List[FundDataResult]:
        snapshots = await self._get_snapshots(codes, refresh=refresh, wait_all=wait_all)
        results = {code: self._select_result(code, snapshots[code]) for code in dict.fromkeys(codes)}
        for row in results.values():
            if row.name and row.name != row.code:
                self._name_cache[row.code] = row.name
        return [results[code] for code in codes]

    async def fetch_single(self, code: str, refresh: bool = False, wait_all: bool = True) -> FundDataResult:
        return (await self.fetch_batch([code], refresh=refresh, wait_all=wait_all))[0]

    async def compare_sources(self, code: str, refresh: bool = False, wait_all: bool = True) -> Dict[str, Any]:
        snapshot = (await self._get_snapshots([code], refresh=refresh, wait_all=wait_all))[code]
        sources = []
        for source, priority in DATA_SOURCE_COMPARISON_SOURCES:
            result = snapshot[source]
            kind, label = _classify_data_kind(source, result.update_time)
            kind = result.data_kind or kind
            if result.is_pending:
                kind, label = "unavailable", "采集中"
            elif kind == "latest_nav":
                label = "最新净值"
            elif not result.is_realtime:
                label = "过期估值"
            sources.append({"source": source, **get_data_source_metadata(source), "priority": priority,
                    "name": result.name, "estimate_nav": result.nav if result.is_success else None,
                    "estimate_change_pct": result.change_pct if result.is_success else None,
                    "last_nav": result.previous_nav, "last_nav_date": result.previous_nav_date,
                    "last_nav_source": result.previous_nav_source,
                    "last_change_pct": result.daily_change,
                    "update_time": result.update_time or "--", "data_kind": kind, "data_kind_label": label,
                    "is_available": result.is_success, "is_realtime": result.is_realtime, "is_pending": result.is_pending,
                    "is_fresh": result.is_realtime, "error": result.error, "stale_reason": result.stale_reason,
                    "data_timestamp": result.fetched_at,
                    "fetch_started_at": result.fetch_started_at,
                    "quality": asdict(describe_quote_quality(
                        source=source, data_kind=kind, source_time=result.update_time,
                        nav_date=result.previous_nav_date, nav_source=result.previous_nav_source,
                        fetched_at=result.fetched_at, available=result.is_success, is_realtime=result.is_realtime,
                        error=result.error, stale_reason=result.stale_reason, fund_type=result.fund_type,
                        pending_sources=[source] if result.is_pending else [])),
                    "fetch_duration_ms": round(result.fetch_duration_ms, 1)})
        usable = [s for s in sources if s["is_available"]]
        selected = self._select_result(code, snapshot)
        best = next((row for row in sources if row["source"] == selected.source), None) if selected.is_success else None
        return {"sources": sources, "best_source": best["source"] if best else None,
                "best_source_display_name": best["display_name"] if best else None,
                "total_sources": len(usable), "realtime_sources": sum(s["is_realtime"] for s in sources),
                "pending_sources": selected.pending_sources, "primary_source_complete": selected.primary_source_complete}

    async def get_fund_name(self, code: str) -> str:
        if code not in self._name_cache:
            result = await self.fetch_single(code)
            if result.name and result.name != code:
                self._name_cache[code] = result.name
        return self._name_cache.get(code, code)

    def close(self):
        self._eastmoney.session.close()
        self._sina.session.close()
        self._dayfund.close()
        self._fund123.close()


_data_source: Optional[DataSourceManager] = None


def get_data_source() -> DataSourceManager:
    global _data_source
    if _data_source is None:
        _data_source = DataSourceManager()
    return _data_source
