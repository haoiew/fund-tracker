"""同刻比较免费估值源；GET/POST 仅用于对照，不重复注册生产源，不保存 Cookie/CSRF。"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import re
import statistics
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit

import requests

from check_estimate_coverage import EastmoneyDirectAdapter, SinaFundAdapter, probe_tiantian, probe_sina, shanghai_now
from app.core.data_source import FundDataResult, SHANGHAI, _number

# ==================== 用户配置 ====================
DEFAULT_CODES = ["012414", "015916", "018125", "016531", "012349", "017641"]
DEFAULT_ROUNDS = 10
DEFAULT_INTERVAL_SECONDS = 15
SINGLE_SOURCE_CONCURRENCY = 2
TIMEOUT = (3, 5)
REPORT_DIRECTORY = Path(__file__).with_name("reports")
SOURCE_SCRIPTS = {
    "tiantian": "https://h5.1234567.com.cn/app/fund-details/js/chunk-common.95006af8.js",
    "dayfund": "https://fund.dayfund.com.cn/templetes/qtx/js/common.js?v1",
    "sina": "https://n.sinaimg.cn/finance/fund/quotes/index.js",
    "fund123": "https://gw.alipayobjects.com/a/finfundpcbff/fundMatiaria-4d369de21fef60c73b5b.js",
}
# ==================================================


def percentile(values, percent):
    values = sorted(values)
    if not values:
        return None
    position = (len(values) - 1) * percent / 100
    lower = math.floor(position)
    upper = math.ceil(position)
    return round(values[lower] + (values[upper] - values[lower]) * (position - lower), 2)


def quote_age_seconds(quote, observed_at):
    stamp = quote.get("update_time")
    if quote.get("data_kind") != "realtime_estimate" or not stamp or ":" not in stamp:
        return None
    try:
        quoted, observed = datetime.fromisoformat(stamp), datetime.fromisoformat(observed_at)
        quoted = quoted.replace(tzinfo=SHANGHAI) if quoted.tzinfo is None else quoted
        observed = observed.replace(tzinfo=SHANGHAI) if observed.tzinfo is None else observed
        return round((observed - quoted).total_seconds(), 2)
    except (ValueError, TypeError):
        return None


def valid_quote(code, source, nav, change, stamp, baseline=None, baseline_date=None):
    nav, change, baseline = _number(nav, positive=True), _number(change), _number(baseline, positive=True)
    result = FundDataResult(code=code, source=source, nav=nav, change_pct=change,
                           update_time=stamp, data_kind="realtime_estimate",
                           previous_nav=baseline, previous_nav_date=baseline_date)
    if nav is None or change is None or change <= -100:
        result.error = "无有效估值或涨跌幅"
    elif baseline is not None and abs(nav - baseline * (1 + change / 100)) > .00015:
        result.error = "估值、涨跌幅与公布净值不一致"
    return result


def parse_dayfund(code, body):
    fields = body.strip().split("|")
    if len(fields) < 11:
        return FundDataResult(code=code, source="dayfund", error="无完整估值字段")
    # 官方 common.js 的 #fvr_net、#fvr_add、#fvr_dt 分别使用 7、6/5、9/10。
    return valid_quote(code, "dayfund", fields[7], fields[5].rstrip("%"),
                       f"{fields[9]} {fields[10]}", fields[1], fields[0])


def parse_fund123(code, payload, baseline):
    rows = payload.get("list") if isinstance(payload, dict) and payload.get("success") is True else None
    rows = [r for r in (rows or []) if isinstance(r, dict) and _number(r.get("time"), positive=True) is not None]
    if not rows:
        return FundDataResult(code=code, source="fund123", error="无有效估值分时点"), None
    last = max(rows, key=lambda r: float(r["time"]))
    try:
        stamp = datetime.fromtimestamp(float(last["time"]) / 1000, SHANGHAI).isoformat()
    except (ValueError, OverflowError, OSError):
        return FundDataResult(code=code, source="fund123", error="无效行情时间戳"), last
    growth = _number(last.get("forecastGrowth"))
    # 官方图表 formatter 将 forecastGrowth * 100 后显示百分数。
    return valid_quote(code, "fund123", last.get("forecastNetValue"),
                       growth * 100 if growth is not None else None, stamp, baseline), last


def pack_quote(row):
    return {**asdict(row), "is_current_estimate": row.is_realtime}


def fetch_single(source, code, session, metadata):
    start = time.perf_counter()
    status = None
    try:
        if source == "dayfund":
            response = session.get("https://fund.dayfund.com.cn/ajs/ajaxdata.shtml",
                                   params={"showtype": "getfundvalue", "fundcode": code},
                                   headers={"Referer": f"https://fund.dayfund.com.cn/fundpre/{code}.html"}, timeout=TIMEOUT)
            status = response.status_code
            response.raise_for_status()
            response.encoding = "utf-8"
            row = parse_dayfund(code, response.text)
            evidence = {"raw_fields": response.text.strip().split("|")}
            business_ok = len(evidence["raw_fields"]) >= 5 and _number(evidence["raw_fields"][1], positive=True) is not None
        else:
            now = shanghai_now()
            response = session.post("https://www.fund123.cn/api/fund/queryFundEstimateIntraday",
                                    params={"_csrf": metadata["csrf"]},
                                    json={"startTime": now.strftime("%Y-%m-%d"),
                                          "endTime": (now + timedelta(days=1)).strftime("%Y-%m-%d"),
                                          "limit": 200, "productId": metadata["product_id"],
                                          "format": True, "source": "WEALTHBFFWEB"}, timeout=TIMEOUT)
            status = response.status_code
            response.raise_for_status()
            payload = response.json()
            row, last = parse_fund123(code, payload, metadata["baseline_nav"])
            evidence = {"latest_raw_point": last, "point_count": len(payload.get("list") or []),
                        "baseline_nav": metadata["baseline_nav"]}
            business_ok = payload.get("success") is True and isinstance(payload.get("list"), list)
        error = None if business_ok else "无有效业务响应"
    except (requests.RequestException, ValueError, TypeError, KeyError) as exc:
        # 异常字符串可能含完整请求 URL 和 CSRF；只记录类型，不输出秘密。
        error = type(exc).__name__
        row = FundDataResult(code=code, source=source, error=error)
        evidence, business_ok = {}, False
    return {"code": code, "http_status": status, "business_success": business_ok,
            "duration_ms": round((time.perf_counter() - start) * 1000, 2),
            "quote": pack_quote(row), "error": error, **evidence}


def init_candidate(source, code):
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0"
    meta = {}
    start = time.perf_counter()
    if source == "fund123":
        url = f"https://www.fund123.cn/matiaria?fundCode={code}"
        session.headers["Referer"] = url
        response = session.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        response.encoding = "utf-8"
        page = response.text
        meta = {"csrf": re.search(r'"csrf":"([^"\r\n]+)"', page).group(1),
                "product_id": re.search(r'"productId":"([^"\r\n]+)"', page).group(1),
                "baseline_nav": _number(re.search(r'"netValue":"([^"\r\n]+)"', page).group(1), positive=True),
                "estimate_downgrade": '"isEstimateDowngrade":true' in page,
                "anonymous": '"isLogin":false' in page}
    return code, session, meta, round((time.perf_counter() - start) * 1000, 2)


def fetch_candidates(source, codes, contexts):
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=SINGLE_SOURCE_CONCURRENCY) as pool:
        rows = list(pool.map(lambda code: fetch_single(source, code, *contexts[code]), codes))
    return {"duration_ms": round((time.perf_counter() - start) * 1000, 2),
            "http_calls": rows, "quotes": [r["quote"] for r in rows]}


def fetch_bulk(source, codes, adapter):
    if source == "sina":
        raw = probe_sina(adapter, codes)
    elif source == "tiantian_get":
        raw = probe_tiantian(adapter, codes, method="GET")  # 仅诊断比较，生产只登记 POST。
    else:
        start = time.perf_counter()
        status = None
        try:
            response = adapter.session.post(adapter.TIANTIAN_URL,
                                            data={"FCODES": ",".join(codes), "FIELDS": adapter.FIELDS}, timeout=TIMEOUT)
            status = response.status_code
            response.raise_for_status()
            payload = response.json()
            if payload.get("success") is not True or not isinstance(payload.get("data"), list):
                raise ValueError("无有效业务数组")
            rows = [adapter._parse_tiantian_row(r) for r in payload["data"] if r.get("FCODE") in codes]
            raw = {"http_status": status, "quotes": [pack_quote(r) for r in rows]}
        except (requests.RequestException, ValueError, TypeError) as exc:
            raw = {"http_status": status, "quotes": [], "error": type(exc).__name__}
        raw["duration_ms"] = round((time.perf_counter() - start) * 1000, 2)
    business_ok = not raw.get("error") and bool(raw.get("quotes"))
    if source == "sina":
        business_ok = business_ok and bool(adapter.ASSIGNMENT.search(raw.get("raw_assignments", "")))
    return {"duration_ms": raw.get("duration_ms"), "quotes": raw.get("quotes", []),
            "http_calls": [{"http_status": raw.get("http_status"), "duration_ms": raw.get("duration_ms"),
                            "business_success": business_ok,
                            "error": raw.get("error")}]}


def summarize(rounds, codes):
    summary = {}
    for source in rounds[0]["sources"]:
        samples = [r["sources"][source] for r in rounds]
        calls = [c for s in samples for c in s["http_calls"]]
        batch_times = [s["duration_ms"] for s in samples if s.get("duration_ms") is not None]
        fresh_counts = [sum(q.get("is_current_estimate", False) for q in s["quotes"]) for s in samples]
        ages = [age for r, s in zip(rounds, samples) for q in s["quotes"]
                if (age := quote_age_seconds(q, r.get("completed_at", ""))) is not None and age >= 0]
        funds = {}
        same_time_values = {}
        for sample in samples:
            for quote in sample["quotes"]:
                if quote.get("data_kind") == "realtime_estimate" and quote.get("nav") is not None:
                    key = (quote["code"], quote.get("update_time"))
                    same_time_values.setdefault(key, set()).add((quote.get("nav"), quote.get("change_pct")))
        for code in codes:
            observations = [next((q for q in s["quotes"] if q["code"] == code), {}) for s in samples]
            stamps = [q.get("update_time") for q in observations if q.get("update_time")]
            funds[code] = {"fresh_rounds": sum(q.get("is_current_estimate", False) for q in observations),
                           "first_timestamp": stamps[0] if stamps else None, "last_timestamp": stamps[-1] if stamps else None,
                           "timestamp_advances": sum(b > a for a, b in zip(stamps, stamps[1:]))}
        summary[source] = {
            "rounds": len(samples), "http_requests": len(calls),
            "http_successes": sum(c.get("http_status") == 200 for c in calls),
            "business_successes": sum(c.get("business_success", False) for c in calls),
            "batch_latency_ms": {"first": batch_times[0] if batch_times else None,
                                 "p50": percentile(batch_times, 50), "p95": percentile(batch_times, 95),
                                 "max": max(batch_times) if batch_times else None},
            "http_latency_ms": {"p50": percentile([c["duration_ms"] for c in calls if c.get("duration_ms") is not None], 50),
                                "p95": percentile([c["duration_ms"] for c in calls if c.get("duration_ms") is not None], 95)},
            "fresh_coverage": {"min": min(fresh_counts), "mean": round(statistics.mean(fresh_counts), 2),
                               "max": max(fresh_counts), "denominator": len(codes)},
            "actual_quote_age_seconds": {"p50": percentile(ages, 50), "p95": percentile(ages, 95),
                                         "max": max(ages) if ages else None},
            "errors": dict(Counter(c["error"] for c in calls if c.get("error"))),
            "quote_unavailability_reasons": dict(Counter(q["error"] for s in samples for q in s["quotes"] if q.get("error"))),
            "same_timestamp_price_conflicts": [
                {"code": code, "timestamp": stamp, "variants": [list(v) for v in values]}
                for (code, stamp), values in same_time_values.items() if len(values) > 1
            ],
            "funds": funds,
        }
    return summary


async def main(args):
    codes = list(dict.fromkeys(c.strip() for c in args.codes.split(",") if c.strip()))
    if not codes or len(codes) > 30 or any(not re.fullmatch(r"\d{6}", c) for c in codes):
        raise ValueError("请提供 1 至 30 个六位代码；货币基金应独立测试")
    adapters = {"tiantian_get": EastmoneyDirectAdapter(), "tiantian_post": EastmoneyDirectAdapter(), "sina": SinaFundAdapter()}
    contexts, bootstrap, proofs = {}, {}, {}
    try:
        for source in ("dayfund", "fund123"):
            start = time.perf_counter()
            with ThreadPoolExecutor(max_workers=SINGLE_SOURCE_CONCURRENCY) as pool:
                prepared = list(pool.map(lambda c: init_candidate(source, c), codes))
            contexts[source] = {code: (session, meta) for code, session, meta, _ in prepared}
            bootstrap[source] = {"wall_ms": round((time.perf_counter() - start) * 1000, 2),
                                 "metadata_get_count": len(codes) if source == "fund123" else 0,
                                 "anonymous_count": sum(meta.get("anonymous", False) for _, _, meta, _ in prepared),
                                 "downgrade_flag_count": sum(meta.get("estimate_downgrade", False) for _, _, meta, _ in prepared)}
        for source, url in SOURCE_SCRIPTS.items():
            response = requests.get(url, timeout=TIMEOUT)
            response.raise_for_status()
            proofs[source] = {"url": url, "sha256": hashlib.sha256(response.content).hexdigest()}
        rounds = []
        for index in range(args.rounds):
            started_at = shanghai_now().isoformat()
            sources = list(adapters) + list(contexts)
            values = await asyncio.gather(*[
                asyncio.to_thread(fetch_bulk, source, codes, adapters[source]) if source in adapters
                else asyncio.to_thread(fetch_candidates, source, codes, contexts[source]) for source in sources
            ])
            rounds.append({"started_at": started_at, "completed_at": shanghai_now().isoformat(), "sources": dict(zip(sources, values))})
            print(f"round={index+1} " + " ".join(f"{s}={sum(q.get('is_current_estimate',False) for q in v['quotes'])}/{len(codes)} {v['duration_ms']}ms" for s, v in zip(sources, values)), flush=True)
            if index + 1 < args.rounds:
                await asyncio.sleep(args.interval_seconds)
        report = {"checked_at": shanghai_now().isoformat(), "timezone": "Asia/Shanghai", "codes": codes,
                  "bootstrap": bootstrap, "script_evidence": proofs, "rounds": rounds, "summary": summarize(rounds, codes),
                  "network": {key: {"host": urlsplit(os.environ[key]).hostname, "port": urlsplit(os.environ[key]).port}
                              for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY") if os.environ.get(key)},
                  "method": {"interval_after_round_seconds": args.interval_seconds, "single_source_concurrency": SINGLE_SOURCE_CONCURRENCY,
                             "bulk_sources": list(adapters), "single_code_sources": list(contexts), "application_cache": "bypassed",
                             "business_response_definition": "校核来源的业务结构；空估值数组不等于网络失败，也不计为估值覆盖。",
                             "quote_age_definition": "实际获取时刻减行情时刻，含已排除的陈旧估值；未按上海收盘钳制。",
                             "limitations": ["本机现有网络路径上的短窗口，不是长期 SLA。", "收盘后计当日最后估值，不把停止交易误判为故障。",
                                             "候选来源未接入生产，未核实再分发授权或估值准确度。", "Fund123 初始化匿名页面/CSRF 的成本单列；不保存 CSRF 或 Cookie。"]}}
        output = Path(args.output) if args.output else REPORT_DIRECTORY / f"realtime_benchmark_{shanghai_now():%Y%m%d_%H%M%S}.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print("report=" + str(output.resolve()), flush=True)
    finally:
        for adapter in adapters.values():
            adapter.session.close()
        for source in contexts.values():
            for session, _ in source.values():
                session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codes", default=",".join(DEFAULT_CODES))
    parser.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS)
    parser.add_argument("--interval-seconds", type=float, default=DEFAULT_INTERVAL_SECONDS)
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.rounds < 1 or args.interval_seconds < 10:
        parser.error("rounds 至少为 1，间隔至少 10 秒，避免密集访问免费源")
    asyncio.run(main(args))
