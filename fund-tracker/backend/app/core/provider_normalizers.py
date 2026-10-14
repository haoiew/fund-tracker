"""Pure provider payload normalization. No sessions, HTTP calls, caches or persistence."""
import json
import re
from datetime import datetime

from app.core import data_contract as contract
from app.core.data_contract import FundDataResult, SHANGHAI, _number

def normalize_eastmoney_nav(row: dict, source: str) -> FundDataResult:
    code = str(row.get("FCODE", "")).strip()
    name = str(row.get("SHORTNAME") or code)
    if row.get("FUNDTYPE") == "005" or "货币" in name:
        return FundDataResult(code=code, name=name, source=source, fund_type="money_market",
                              error="货币基金需查询万份收益和七日年化，不能把收益字段作为单位净值")
    nav = _number(row.get("NAV"), positive=True)
    date = row.get("PDATE")
    try:
        if not date or datetime.fromisoformat(date).date() > contract.shanghai_now().date():
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


def normalize_tiantian(row: dict) -> FundDataResult:
    result = normalize_eastmoney_nav(row, "tiantian")
    if result.fund_type == "money_market":
        return result
    estimate = _number(row.get("GSZ"), positive=True)
    estimate_time = row.get("GZTIME")
    if estimate is not None and contract.is_current_estimate(estimate_time):
        result.nav = estimate
        result.change_pct = _number(row.get("GSZZL"))
        result.update_time = estimate_time
        result.data_kind = "realtime_estimate"
        result.error = None
    elif estimate is not None and not contract.is_current_estimate(estimate_time):
        result.stale_reason = f"估值时刻不满足当前时效要求: {estimate_time}"
    return result


def normalize_sina_quote(code: str, estimate: list[str], official: list[str]) -> FundDataResult:
    name = estimate[0] if estimate and estimate[0] else (official[0] if official else code)
    result = FundDataResult(code=code, name=name, source="sina", data_kind="realtime_estimate")
    if "货币" in name:
        result.fund_type = "money_market"
        result.error = "货币基金收益不是单位净值或盘中估值"
        return result
    if len(official) >= 5:
        unit_nav = _number(official[1], positive=True)
        try:
            date = datetime.strptime(official[4], "%Y-%m-%d").date()
        except ValueError:
            date = None
        if unit_nav is not None and date is not None and date <= contract.shanghai_now().date():
            result.previous_nav, result.previous_nav_date = unit_nav, date.isoformat()
            result.accumulated_nav = _number(official[2], positive=True)
            # f 行情未给正式日增长率；单位净值比值可能漏掉分红，不冒充该字段。
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
    if not contract.is_current_estimate(stamp):
        result.error = "新浪估值时刻不满足当前时效要求"
        result.stale_reason = f"估值时刻不满足当前时效要求: {stamp}"
        return result
    result.nav, result.change_pct, result.update_time = nav, change, stamp
    return result


def normalize_dayfund(code: str, body: str) -> FundDataResult:
    fields = body.strip().split("|")
    if len(fields) < 11:
        return FundDataResult(code=code, source="dayfund", error="净值估算网无完整估值字段")
    # common.js: #fvr_net=7, #fvr_add=6/5, #fvr_dt=9/10；1 是正式单位净值。
    baseline = _number(fields[1], positive=True)
    try:
        date = datetime.strptime(fields[0], "%Y-%m-%d").date()
        valid_date = date <= contract.shanghai_now().date()
    except ValueError:
        valid_date = False
    result = FundDataResult(code=code, source="dayfund", data_kind="realtime_estimate",
                            nav=_number(fields[7], positive=True), change_pct=_number(fields[5].rstrip("%")),
                            update_time=f"{fields[9]} {fields[10]}",
                            previous_nav=baseline if valid_date else None,
                            previous_nav_date=fields[0] if valid_date and baseline is not None else None,
                            accumulated_nav=_number(fields[2], positive=True),
                            daily_change=_number(fields[4].rstrip("%")))
    return check_provider_estimate(result, baseline)


def normalize_fund123(code: str, payload, baseline=None, name=None) -> FundDataResult:
    rows = payload.get("list") if isinstance(payload, dict) and payload.get("success") is True else None
    rows = [row for row in (rows if isinstance(rows, list) else [])
            if isinstance(row, dict) and _number(row.get("time"), positive=True) is not None]
    if not rows:
        return FundDataResult(code=code, name=name, source="fund123", error="数米无有效估值分时点")
    last = max(rows, key=lambda row: float(row["time"]))
    try:
        stamp = datetime.fromtimestamp(float(last["time"]) / 1000, SHANGHAI).isoformat()
    except (ValueError, OverflowError, OSError):
        return FundDataResult(code=code, source="fund123", error="数米无效行情时间戳")
    growth = _number(last.get("forecastGrowth"))
    result = FundDataResult(code=code, name=name, source="fund123", data_kind="realtime_estimate",
                            nav=_number(last.get("forecastNetValue"), positive=True),
                            change_pct=growth * 100 if growth is not None else None, update_time=stamp)
    # SSR 日期仅 MM-DD，不能拼接年份冒充完整的官方净值日。
    return check_provider_estimate(result, _number(baseline, positive=True))


def check_provider_estimate(result: FundDataResult, baseline=None) -> FundDataResult:
    """平台估值仍需检查字段、比例和真实行情时刻，HTTP 200 不是成功标准。"""
    if result.nav is None or result.change_pct is None or result.change_pct <= -100:
        result.error = "无有效估值或涨跌幅"
    elif baseline is not None and abs(result.nav - baseline * (1 + result.change_pct / 100)) > .00015:
        result.error = "估值、基准单位净值与涨跌幅不一致"
    elif not contract.is_current_estimate(result.update_time):
        result.error = "估值时刻不满足当前时效要求"
        result.stale_reason = f"估值时刻不满足当前时效要求: {result.update_time}"
    if result.error:
        result.nav = None
    return result


SINA_ASSIGNMENT = re.compile(r'var\s+hq_str_(f|fu)_(\d{6})\s*=\s*"([^"\r\n]*)"\s*;')


def normalize_sina(codes: list[str], body: str) -> list[FundDataResult]:
    fields = {(kind, code): value.split(",") for kind, code, value in SINA_ASSIGNMENT.findall(body)
              if code in codes}
    return [normalize_sina_quote(code, fields.get(("fu", code), []), fields.get(("f", code), [])) for code in codes]


def normalize_tencent(code: str, body: str) -> FundDataResult:
    if "v_jj" in body:
        parts = body.split('="', 1)[1].strip('";\n').split('~')
        if len(parts) > 8:
            name = parts[1] or code
            if "货币" in name:
                return FundDataResult(code=code, name=name, source="tencent", fund_type="money_market",
                                      error="货币基金收益不是单位净值")
            nav = _number(parts[2], positive=True) or _number(parts[5], positive=True)
            if nav and parts[8]:
                return FundDataResult(code=code, name=name, nav=nav, change_pct=_number(parts[7]),
                                      update_time=parts[8], source="tencent", data_kind="latest_nav")
    return FundDataResult(code=code, source="tencent", error="腾讯基金无有效单位净值")


def normalize_lsjz(code: str, payload: dict) -> FundDataResult:
    data = payload.get("Data") or {}
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
    return FundDataResult(code=code, source="eastmoney_lsjz", error="东方财富历史净值接口无有效数据")


def normalize_pingzhongdata(code: str, body: str) -> FundDataResult:
    match = re.search(r'Data_netWorthTrend\s*=\s*(\[.*?\]);', body, re.DOTALL)
    if match:
        rows = json.loads(match.group(1))
        if rows:
            last = rows[-1]
            nav = _number(last.get("y"), positive=True)
            if nav and last.get("x"):
                stamp = datetime.fromtimestamp(last["x"] / 1000, SHANGHAI).date().isoformat()
                return FundDataResult(code=code, nav=nav, change_pct=_number(last.get("equityReturn")),
                                      update_time=stamp, source="pingzhongdata", data_kind="latest_nav")
    return FundDataResult(code=code, source="pingzhongdata", error="基金页面无有效单位净值走势")
