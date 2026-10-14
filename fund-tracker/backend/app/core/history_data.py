"""规范化历史单位净值、累计净值和来源日增长率；收益基准明确保留。"""
import json
import re
import math

import pandas as pd


def normalize_nav_history(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["净值日期"] = pd.to_datetime(frame["净值日期"], errors="coerce").dt.normalize()
    frame["单位净值"] = pd.to_numeric(frame["单位净值"], errors="coerce")
    frame = frame[frame["净值日期"].notna() & frame["单位净值"].notna() & frame["单位净值"].map(math.isfinite) & (frame["单位净值"] > 0)]
    frame = frame.sort_values("净值日期").drop_duplicates("净值日期", keep="last").reset_index(drop=True)
    if "累计净值" not in frame:
        frame["累计净值"] = None
    frame["累计净值"] = pd.to_numeric(frame["累计净值"], errors="coerce")
    growth = pd.to_numeric(frame.get("provider_change_pct", pd.Series(index=frame.index, dtype=float)), errors="coerce") / 100
    growth = growth.where(growth.map(math.isfinite) & (growth > -1))
    frame["pct_change"] = growth.where(growth.notna(), frame["单位净值"].pct_change(fill_method=None))
    frame["return_basis"] = growth.notna().map({True: "provider_daily_growth", False: "unit_nav_price_change"})
    frame["return_index"] = (1 + frame["pct_change"].fillna(0)).cumprod()
    return frame


def parse_pingzhong_history(text: str) -> pd.DataFrame:
    def extract(name):
        match = re.search(rf"\b{re.escape(name)}\s*=\s*(\[.*?\]);", text, re.S)
        return json.loads(match.group(1)) if match else []

    rows = extract("Data_netWorthTrend")
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows).rename(columns={"y": "单位净值", "equityReturn": "provider_change_pct"})
    frame["净值日期"] = pd.to_datetime(frame["x"], unit="ms", utc=True).dt.tz_convert("Asia/Shanghai").dt.tz_localize(None)
    accumulated = extract("Data_ACWorthTrend")
    if accumulated:
        accumulated_frame = pd.DataFrame(accumulated, columns=["x", "累计净值"])
        accumulated_frame["净值日期"] = pd.to_datetime(accumulated_frame["x"], unit="ms", utc=True).dt.tz_convert("Asia/Shanghai").dt.tz_localize(None).dt.normalize()
        frame["净值日期"] = frame["净值日期"].dt.normalize()
        frame = frame.merge(accumulated_frame[["净值日期", "累计净值"]], on="净值日期", how="left")
    return normalize_nav_history(frame)


def parse_lsjz_history(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows).rename(columns={
        "FSRQ": "净值日期", "DWJZ": "单位净值", "LJJZ": "累计净值", "JZZZL": "provider_change_pct",
    })
    return normalize_nav_history(frame)


def calculate_period_returns(dates, values) -> dict:
    """按日历周期从财富/价格序列取区间收益，不对累计收益曲线再次复利。"""
    offsets = {
        "d3": pd.DateOffset(days=3), "d7": pd.DateOffset(days=7), "d30": pd.DateOffset(days=30),
        "m3": pd.DateOffset(months=3), "m6": pd.DateOffset(months=6),
        "y1": pd.DateOffset(years=1), "y3": pd.DateOffset(years=3), "y5": pd.DateOffset(years=5),
    }
    returns = dict.fromkeys(offsets)
    periods = {}
    frame = pd.DataFrame({"date": pd.to_datetime(list(dates)), "value": list(values)}).sort_values("date")
    if not frame.empty:
        last = frame.iloc[-1]
        for key, offset in offsets.items():
            cutoff = last["date"] - offset
            eligible = frame[frame["date"] <= cutoff]
            if eligible.empty:
                continue
            base = eligible.iloc[-1]
            if base["value"] <= 0 or not math.isfinite(base["value"]) or not math.isfinite(last["value"]):
                continue
            returns[key] = float((last["value"] / base["value"] - 1) * 100)
            periods[key] = {"from": base["date"].date().isoformat(), "to": last["date"].date().isoformat()}
    return {"returns": returns, "return_period_dates": periods, "period_basis": "calendar_ending_at_last_observation"}
