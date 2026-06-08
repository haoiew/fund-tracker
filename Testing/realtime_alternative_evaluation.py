# -*- coding: utf-8 -*-
"""
Evaluate fallback choices for funds without intraday realtime estimates.

This is an evaluation harness only. It does not change production data paths.
Run from the repository root with:
    conda run --no-capture-output -n fund-tracker python Testing/realtime_alternative_evaluation.py
"""
from __future__ import annotations

import argparse
import asyncio
import html
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import requests


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "fund-tracker" / "backend"
DEFAULT_CASES = [
    ("005051", "摩根标普港股通低波红利指数A"),
    ("160125", "南方香港优选股票"),
    ("012709", "东方红中证红利低波动指数C"),
    ("519674", "银河创新成长混合A"),
]
SIMILAR_CANDIDATE_LIMIT = 8
QUOTE_TIMEOUT_SECONDS = 5
MIN_HOLDING_QUOTE_COVERAGE = 0.6


sys.path.insert(0, str(BACKEND_DIR))

from app.services.fund_service import get_fund_service  # noqa: E402


def _extract_js_var(text: str, var_name: str) -> Any | None:
    match = re.search(rf"var\s+{re.escape(var_name)}\s*=\s*(.*?);", text, re.S)
    if not match:
        return None
    raw = match.group(1).strip()
    try:
        return json.loads(raw)
    except Exception:
        return None


def _stock_quote_symbol(raw_code: str) -> str | None:
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
    if not code:
        return None
    if re.fullmatch(r"\d{6}", code):
        return ("sh" if code.startswith(("5", "6", "9")) else "sz") + code
    if re.fullmatch(r"\d{5}", code):
        return "hk" + code
    if re.fullmatch(r"\d{1,4}", code):
        return "hk" + code.zfill(5)
    if re.fullmatch(r"[a-z.]{1,8}", code):
        return "us" + code.upper()
    return None


def _fetch_tencent_quote_changes(symbols: list[str]) -> dict[str, float]:
    if not symbols:
        return {}
    session = requests.Session()
    result: dict[str, float] = {}
    for chunk_start in range(0, len(symbols), 50):
        chunk = symbols[chunk_start:chunk_start + 50]
        url = "http://qt.gtimg.cn/q=" + ",".join(chunk)
        resp = session.get(url, timeout=QUOTE_TIMEOUT_SECONDS)
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


def _fetch_f10_top_holdings(code: str) -> dict[str, Any]:
    url = "https://fundf10.eastmoney.com/FundArchivesDatas.aspx"
    params = {
        "type": "jjcc",
        "code": code,
        "topline": "10",
        "year": "",
        "month": "",
        "rt": str(time.time()),
    }
    headers = {"Referer": f"https://fundf10.eastmoney.com/ccmx_{code}.html"}
    resp = requests.get(url, params=params, headers=headers, timeout=QUOTE_TIMEOUT_SECONDS)
    resp.raise_for_status()
    text = html.unescape(resp.text)
    date_match = re.search(r"截止至：<font[^>]*>([^<]+)</font>", text)
    position_date = date_match.group(1).strip() if date_match else None

    holdings = []
    for row_match in re.finditer(r"<tr>(.*?)</tr>", text, re.S):
        row = row_match.group(1)
        if "quote.eastmoney.com/unify/r/" not in row:
            continue
        market_match = re.search(r"quote\.eastmoney\.com/unify/r/([^']+)'[^>]*>([^<]+)</a>", row)
        link_labels = re.findall(r"quote\.eastmoney\.com/unify/r/[^']+'[^>]*>([^<]+)</a>", row)
        weight_match = re.search(r"<td[^>]*>([\d.]+)%</td>", row)
        if not market_match or len(link_labels) < 2 or not weight_match:
            continue
        market_code, stock_code = market_match.groups()
        stock_name = link_labels[1]
        weight_raw = weight_match.group(1)
        symbol = _stock_quote_symbol(market_code) or _stock_quote_symbol(stock_code)
        if not symbol:
            continue
        holdings.append({
            "code": stock_code,
            "symbol": symbol,
            "name": stock_name,
            "weight": float(weight_raw),
        })

    return {"position_date": position_date, "holdings": holdings}


def evaluate_holdings_estimate(code: str) -> dict[str, Any]:
    url = f"http://fund.eastmoney.com/pingzhongdata/{code}.js?rt={int(time.time() * 1000)}"
    try:
        resp = requests.get(url, timeout=QUOTE_TIMEOUT_SECONDS)
        resp.raise_for_status()
    except Exception as exc:
        return {"feasible": False, "reason": f"holdings_source_failed: {exc}"}

    content = resp.text
    stock_codes = _extract_js_var(content, "stockCodesNew") or _extract_js_var(content, "stockCodes") or []
    positions = _extract_js_var(content, "Data_fundSharesPositions") or []
    try:
        holding_payload = _fetch_f10_top_holdings(code)
        holdings = holding_payload["holdings"]
        position_date = holding_payload["position_date"]
    except Exception as exc:
        holdings = []
        position_date = None
        f10_error = str(exc)
    else:
        f10_error = None

    if not holdings:
        return {
            "feasible": False,
            "reason": "no_parseable_f10_holdings_with_weights",
            "stock_code_count": len(stock_codes),
            "position_group_count": len(positions),
            "f10_error": f10_error,
        }

    quote_changes = _fetch_tencent_quote_changes([item["symbol"] for item in holdings])
    quoted = [item for item in holdings if item["symbol"] in quote_changes]
    total_weight = sum(item["weight"] for item in holdings)
    quoted_weight = sum(item["weight"] for item in quoted)
    coverage = quoted_weight / total_weight if total_weight else 0

    weighted_change = None
    if quoted_weight:
        weighted_change = sum(item["weight"] * quote_changes[item["symbol"]] for item in quoted) / quoted_weight

    return {
        "feasible": coverage >= MIN_HOLDING_QUOTE_COVERAGE,
        "reason": "ok" if coverage >= MIN_HOLDING_QUOTE_COVERAGE else "quote_coverage_too_low",
        "holding_count": len(holdings),
        "position_date": position_date,
        "quoted_count": len(quoted),
        "quoted_weight_coverage": round(coverage, 4),
        "weighted_stock_change_pct": round(weighted_change, 4) if weighted_change is not None else None,
        "top_holdings": [
            {
                "code": item["code"],
                "name": item["name"],
                "weight": item["weight"],
                "quote_change_pct": quote_changes.get(item["symbol"]),
            }
            for item in holdings[:10]
        ],
    }


async def evaluate_case(code: str, name: str) -> dict[str, Any]:
    service = get_fund_service()
    direct = await service.get_realtime_data(code)
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
            "alternative_evaluation": "skipped_direct_realtime_available",
        }

    comparison = await service.get_data_source_comparison(code, name)
    search_keyword = name if name and name != code else direct.name
    candidates = service.search_funds(search_keyword, SIMILAR_CANDIDATE_LIMIT)
    candidate_codes = [item["code"] for item in candidates if item.get("code") and item["code"] != code]
    realtime_candidates = []
    if candidate_codes:
        candidate_rows = await service.get_realtime_batch(candidate_codes)
        realtime_candidates = [
            {
                "code": row.code,
                "name": row.name,
                "change_pct": float(row.estimate_change) if row.estimate_change is not None else None,
                "update_time": row.update_time,
                "source": row.data_source,
                "is_realtime": row.is_realtime,
            }
            for row in candidate_rows
            if row.is_realtime
        ]

    exchange_sources = [
        {
            "source": item["source"],
            "change_pct": item["estimate_change_pct"],
            "update_time": item["update_time"],
            "is_realtime": item["is_realtime"],
        }
        for item in comparison["sources"]
        if item["source"] in {"tencent", "tiantian"} and item["is_fresh"]
    ]

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
        "same_name_realtime_candidates": realtime_candidates,
        "exchange_or_quote_sources": exchange_sources,
        "holdings_based_estimate": evaluate_holdings_estimate(code),
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", action="append", help="Fund case as code:name. Can repeat.")
    args = parser.parse_args()
    cases = []
    for item in args.case or []:
        code, _, name = item.partition(":")
        cases.append((code.strip(), name.strip() or code.strip()))
    if not cases:
        cases = DEFAULT_CASES

    results = [await evaluate_case(code, name) for code, name in cases]
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
