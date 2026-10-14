"""独立核对天天/新浪的原始估值覆盖和时效；不读写用户持仓或历史数据库。"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import sys
import time
from dataclasses import asdict
from pathlib import Path
from collections import Counter

import requests

# ==================== 用户配置 ====================
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FUND_FILE = Path(__file__).with_name("funds.txt")
EXTRA_CODES = ["000001", "161725", "017470", "005051", "519674", "110022", "000198", "015915", "018124"]
SINA_PAGE_SCRIPT = "https://n.sinaimg.cn/finance/fund/quotes/index.js"
DEFAULT_ROUNDS = 2
DEFAULT_INTERVAL_SECONDS = 15
REPORT_DIRECTORY = Path(__file__).with_name("reports")
# ==================================================

sys.path.insert(0, str(REPOSITORY_ROOT / "fund-tracker" / "backend"))
from app.core.data_source import EastmoneyDirectAdapter, SinaFundAdapter, shanghai_now  # noqa: E402


def probe_tiantian(adapter, codes, method="POST"):
    start = time.perf_counter()
    try:
        fields = {"FCODES": ",".join(codes), "FIELDS": adapter.FIELDS}
        response = adapter.session.request(method, adapter.TIANTIAN_URL,
                                           **{"data" if method == "POST" else "params": fields}, timeout=(3, 5))
        response.raise_for_status()
        payload = response.json()
        if payload.get("success") is not True or not isinstance(payload.get("data"), list):
            raise ValueError("无有效天天业务数据")
        raw = [r for r in payload["data"] if isinstance(r, dict) and r.get("FCODE") in codes]
        quotes = [adapter._parse_tiantian_row(r) for r in raw]
        return {"http_status": response.status_code, "raw_fields": raw,
                "quotes": [{**asdict(r), "is_current_estimate": r.is_realtime} for r in quotes],
                "current_estimate_count": sum(r.is_realtime for r in quotes),
                "duration_ms": round((time.perf_counter() - start) * 1000, 1)}
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}", "quotes": [], "current_estimate_count": 0}


def probe_sina(adapter, codes):
    start = time.perf_counter()
    try:
        response = adapter.session.get(adapter.build_quote_url(codes),
                                       timeout=(3, 5))
        response.raise_for_status()
        response.encoding = "gb18030"
        quotes = adapter.parse_response(codes, response.text)
        return {"http_status": response.status_code, "raw_assignments": response.text,
                "quotes": [{**asdict(r), "is_current_estimate": r.is_realtime} for r in quotes],
                "current_estimate_count": sum(r.is_realtime for r in quotes),
                "duration_ms": round((time.perf_counter() - start) * 1000, 1)}
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}", "quotes": [], "current_estimate_count": 0}


def verify_sina_mapping(adapter):
    try:
        response = adapter.session.get(SINA_PAGE_SCRIPT, timeout=(3, 5))
        response.raise_for_status()
        body = response.text
        return {"url": SINA_PAGE_SCRIPT, "http_status": response.status_code,
                "sha256": hashlib.sha256(response.content).hexdigest(),
                "page_uses_estimate_field_2": bool(re.search(r'zxgz_data.{0,80}fund_hq_data\[2\]', body)),
                "page_uses_change_field_6": 'fund_hq_data[6]' in body,
                "page_uses_date_7_time_1": 'fund_hq_data[7]' in body and 'fund_hq_data[1]' in body,
                "note": "字段按新浪自身 latestValuation 核对；未使用 fu[8]/fu[9] 的另一组值。"}
    except Exception as exc:
        return {"url": SINA_PAGE_SCRIPT, "error": type(exc).__name__}


def check_api_loading(base, sample_codes):
    """真实 API 分阶段计时，只保存价格与覆盖，不导出持仓金额/份额。"""
    with requests.Session() as session:
        session.trust_env = False  # 本地验证不绕路系统 HTTP 代理。

        def request(method, path, **kwargs):
            start = time.perf_counter()
            response = session.request(method, base.rstrip("/") + path, timeout=(3, 40), **kwargs)
            response.raise_for_status()
            return response.json()["data"], round((time.perf_counter() - start) * 1000, 1)

        cache_before, _ = request("GET", "/system/cache/stats")
        metadata, metadata_ms = request("GET", "/portfolio/summary?include_quotes=false")
        holdings = list(dict.fromkeys(r["fund_code"] for r in metadata["items"]))
        codes = list(dict.fromkeys(sample_codes + holdings))
        fields = ["code", "name", "estimate_nav", "estimate_change", "update_time", "data_source", "data_kind",
                  "is_realtime", "is_inferred", "official_nav", "official_update_time", "status", "error"]
        rounds = []
        for _ in range(2):
            provider, provider_ms = request("POST", "/funds/realtime/batch", params={"view": "provider"}, json=codes)
            auto, auto_ms = request("POST", "/funds/realtime/batch", params={"view": "auto"}, json=codes)
            by_code = {r["code"]: r for r in auto}
            rounds.append({"requested_count": len(codes), "provider_ms": provider_ms, "auto_ms": auto_ms,
                           "quote_phase_ms": round(provider_ms + auto_ms, 1),
                           "provider_count": sum(r["is_realtime"] for r in provider),
                           "priced_count": sum(r["estimate_nav"] is not None for r in auto),
                           "source_counts": dict(Counter(r["data_source"] for r in auto)),
                           "holding_count": len(holdings),
                           "holding_priced_count": sum(by_code[c]["estimate_nav"] is not None for c in holdings),
                           "quotes": [{k: r.get(k) for k in fields} for r in auto]})
        manual_nav, _ = request("POST", "/funds/realtime/batch", params={"view": "nav"}, json=["015916", "018125"])
        portfolio, portfolio_ms = request("GET", "/portfolio/summary")
        comparisons = []
        for code in ("012414", "015916", "018125"):
            data, elapsed = request("GET", f"/funds/{code}/data-sources")
            comparisons.append({"code": code, "duration_ms": elapsed, **data})
        return {"api_base": base, "checked_at": shanghai_now().isoformat(), "cache_before": cache_before,
                "metadata_ms": metadata_ms, "rounds": rounds, "source_comparisons": comparisons,
                "manual_nav": [{k: r.get(k) for k in fields} for r in manual_nav],
                "portfolio_summary": {"rows": len(portfolio["items"]), "duration_ms": portfolio_ms,
                                      "priced_rows": sum(r["current_nav"] is not None for r in portfolio["items"])},
                "note": "缓存状态只指本应用内存，非上游/CDN 冷缓存；不含浏览器绘制。仅 GET/报价 POST，无持仓增删。"}


async def main(args):
    codes = args.codes.split(",") if args.codes else FUND_FILE.read_text(encoding="utf-8").splitlines() + EXTRA_CODES
    codes = list(dict.fromkeys(c.strip() for c in codes if c.strip()))
    if not codes or len(codes) > 100 or any(not re.fullmatch(r"\d{6}", c) for c in codes):
        raise ValueError("请提供 1 至 100 个六位基金代码")
    tiantian, sina = EastmoneyDirectAdapter(), SinaFundAdapter()
    try:
        mapping = await asyncio.to_thread(verify_sina_mapping, sina)
        rounds = []
        for index in range(args.rounds):
            # 与生产一样并发取源；此脚本只保留天天和新浪的原始字段专项核查。
            checked_at = shanghai_now().isoformat()
            tt, sn = await asyncio.gather(asyncio.to_thread(probe_tiantian, tiantian, codes),
                                         asyncio.to_thread(probe_sina, sina, codes))
            covered = {r["code"] for source in (tt, sn) for r in source["quotes"] if r["is_current_estimate"]}
            rounds.append({"started_at": checked_at, "completed_at": shanghai_now().isoformat(),
                           "requested_count": len(codes), "union_current_estimate_count": len(covered),
                           "tiantian": tt, "sina": sn})
            print(f"round={index + 1} tiantian={tt['current_estimate_count']} sina={sn['current_estimate_count']} "
                  f"union={len(covered)}/{len(codes)}")
            if index + 1 < args.rounds:
                await asyncio.sleep(args.interval_seconds)
        report = {"checked_at": shanghai_now().isoformat(), "timezone": "Asia/Shanghai", "codes": codes,
                  "sina_field_mapping": mapping, "rounds": rounds,
                  "limitations": ["接口当次可用不代表 SLA、全市场覆盖、估值准确度或再分发授权。",
                                  "两源覆盖并集是候选覆盖，不替代生产的净值一致性和显示选择规则。"]}
        if args.api_base:
            sample = args.codes.split(",") if args.codes else FUND_FILE.read_text(encoding="utf-8").splitlines()
            report["api_loading"] = await asyncio.to_thread(check_api_loading, args.api_base, sample)
            for index, result in enumerate(report["api_loading"]["rounds"], start=1):
                print(f"api_round={index} provider_ms={result['provider_ms']} quote_phase_ms={result['quote_phase_ms']} "
                      f"priced={result['priced_count']}/{result['requested_count']}")
        output = Path(args.output) if args.output else REPORT_DIRECTORY / f"estimate_coverage_{shanghai_now():%Y%m%d_%H%M%S}.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"report={output.resolve()}")
    finally:
        tiantian.session.close()
        sina.session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codes", help="逗号分隔基金代码，默认原样本与 A/C、货币基金等补充样本")
    parser.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS)
    parser.add_argument("--interval-seconds", type=float, default=DEFAULT_INTERVAL_SECONDS)
    parser.add_argument("--output", help="JSON 报告路径")
    parser.add_argument("--api-base", help="可选应用 API 根地址，如 http://127.0.0.1:8001/api/v1；增加只读加载计时")
    args = parser.parse_args()
    if args.rounds < 1 or not 0 <= args.interval_seconds <= 60:
        parser.error("rounds 至少为 1；interval-seconds 在 0 到 60 之间")
    asyncio.run(main(args))
