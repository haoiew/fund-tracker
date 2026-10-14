"""使用当前生产适配器核查真实数据，不写入持仓或历史数据库。"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from dataclasses import asdict
from pathlib import Path

# ==================== 用户配置 ====================
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FUND_FILE = Path(__file__).with_name("funds.txt")
EXTRA_CODES = ["000001", "161725", "017470", "005051", "519674", "110022", "000198", "015915", "018124"]
COMPARISON_CODES = ["161725", "015916", "018125", "012709", "160125", "513630"]
AUTO_VIEW_CODES = ["161725", "015916", "018125", "012709", "160125", "513630", "161226"]
REPORT_DIRECTORY = Path(__file__).with_name("reports")
DEFAULT_ROUNDS = 2
DEFAULT_INTERVAL_SECONDS = 10
# ==================================================

sys.path.insert(0, str(REPOSITORY_ROOT / "fund-tracker" / "backend"))

from app.core.data_source import DataSourceManager, shanghai_now  # noqa: E402
from app.services.fund_service import FundService  # noqa: E402


async def check_round(manager: DataSourceManager, codes: list[str]) -> dict:
    start = time.perf_counter()
    rows = await manager.fetch_batch(codes)
    limiter = asyncio.Semaphore(2)

    async def compare(code):
        async with limiter:
            return {"code": code, **await manager.compare_sources(code)}

    comparisons = await asyncio.gather(*(compare(code) for code in COMPARISON_CODES))
    return {
        "checked_at": shanghai_now().isoformat(),
        "duration_ms": round((time.perf_counter() - start) * 1000, 1),
        "requested_count": len(codes),
        "available_count": sum(row.is_success for row in rows),
        "provider_estimate_count": sum(row.is_realtime for row in rows),
        "quotes": [{**asdict(row), "is_available": row.is_success, "is_realtime": row.is_realtime} for row in rows],
        "source_comparisons": comparisons,
    }


def check_retired(manager: DataSourceManager) -> list[dict]:
    session = manager._eastmoney.session
    cases = [
        ("legacy_fundgz", "https://fundgz.1234567.com.cn/js/161725.js"),
        ("tencent_intraday", "https://web.ifzq.gtimg.cn/fund/newfund/fundSsgz/getSsgz?app=web&symbol=jj161725"),
        ("danjuan_estimate", "https://danjuanfunds.com/djapi/fund/estimate-nav/161725"),
    ]
    results = []
    for name, url in cases:
        try:
            response = session.get(url, timeout=(3, 5))
            row = {"name": name, "url": url, "http_status": response.status_code}
            if name == "legacy_fundgz":
                row.update({"has_valuation_payload": bool(re.search(r"jsonpgz\s*\(\s*\{", response.text)),
                            "content_type": response.headers.get("Content-Type")})
            else:
                data = response.json()
                if name == "tencent_intraday":
                    row.update({"business_code": data.get("code"), "message": data.get("msg")})
                else:
                    row.update({"business_code": data.get("result_code"),
                                "estimate_point_count": len((data.get("data") or {}).get("items") or [])})
            results.append(row)
        except Exception as exc:
            results.append({"name": name, "url": url, "error": type(exc).__name__})
    return results


async def main(args):
    file_codes = FUND_FILE.read_text(encoding="utf-8").splitlines()
    codes = args.codes.split(",") if args.codes else file_codes + EXTRA_CODES
    codes = list(dict.fromkeys(code.strip() for code in codes if code.strip()))
    if not codes or any(not re.fullmatch(r"\d{6}", code) for code in codes):
        raise ValueError("请提供有效的六位基金代码列表")
    manager = DataSourceManager()
    service = FundService()
    try:
        rounds = []
        for index in range(args.rounds):
            result = await check_round(manager, codes)
            rounds.append(result)
            print(f"round={index + 1} available={result['available_count']}/{len(codes)} "
                  f"provider_estimates={result['provider_estimate_count']} duration_ms={result['duration_ms']}")
            if index + 1 < args.rounds:
                await asyncio.sleep(args.interval_seconds)
        selected = await service.get_realtime_batch(AUTO_VIEW_CODES)
        history = await asyncio.to_thread(service.get_historical_nav, "161725", 30)
        report = {
            "checked_at": shanghai_now().isoformat(), "timezone": "Asia/Shanghai",
            "rounds": rounds, "auto_view": [row.model_dump(mode="json") for row in selected],
            "retired_endpoints": await asyncio.to_thread(check_retired, manager),
            "history_smoke": {
                "code": "161725", "rows": len(history), "columns": history.columns.tolist(),
                "latest_date": history["净值日期"].iloc[-1].isoformat() if not history.empty else None,
                "latest_unit_nav": float(history["单位净值"].iloc[-1]) if not history.empty else None,
                "latest_accumulated_nav": float(history["累计净值"].iloc[-1]) if not history.empty and history["累计净值"].notna().iloc[-1] else None,
                "return_basis_counts": history["return_basis"].value_counts().to_dict() if not history.empty else {},
                "note": "验证规范化历史读取、上海净值日期、单位/累计净值和收益口径，未写数据库。",
            },
        }
        output = Path(args.output) if args.output else REPORT_DIRECTORY / f"availability_{shanghai_now():%Y%m%d_%H%M%S}.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"report={output.resolve()}")
    finally:
        manager.close()
        service.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codes", help="逗号分隔基金代码，默认原基准列表和额外代表样本")
    parser.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS)
    parser.add_argument("--interval-seconds", type=float, default=DEFAULT_INTERVAL_SECONDS)
    parser.add_argument("--output", help="JSON 报告路径")
    args = parser.parse_args()
    if args.rounds < 1 or not 0 <= args.interval_seconds <= 60:
        parser.error("rounds 必须至少为 1；interval-seconds 必须在 0 到 60 之间")
    asyncio.run(main(args))
