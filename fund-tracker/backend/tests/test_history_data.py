import json
from datetime import datetime, timezone, timedelta

import pytest

from app.core.history_data import parse_pingzhong_history, normalize_nav_history, calculate_period_returns


def test_unit_accumulated_nav_dates_and_dividend_return_are_distinct():
    tz = timezone(timedelta(hours=8))
    t1 = int(datetime(2026, 10, 12, tzinfo=tz).timestamp() * 1000)
    t2 = int(datetime(2026, 10, 13, tzinfo=tz).timestamp() * 1000)
    text = (
        "var Data_netWorthTrend = " + json.dumps([
            {"x": t1, "y": 1.0, "equityReturn": 0},
            {"x": t2, "y": 0.81, "equityReturn": 1},
        ]) + "; var Data_ACWorthTrend = " + json.dumps([[t1, 2.0], [t2, 2.01]]) + ";"
    )
    frame = parse_pingzhong_history(text)
    assert frame["净值日期"].dt.strftime("%Y-%m-%d").tolist() == ["2026-10-12", "2026-10-13"]
    assert frame["单位净值"].tolist() == [1.0, 0.81]
    assert frame["累计净值"].tolist() == [2.0, 2.01]
    assert frame["pct_change"].iloc[-1] == pytest.approx(0.01)
    assert frame["return_index"].iloc[-1] / frame["return_index"].iloc[0] - 1 == pytest.approx(0.01)


def test_missing_accumulated_nav_is_not_fabricated():
    text = 'var Data_netWorthTrend = [{"x":1791734400000,"y":1.2,"equityReturn":0}];'
    frame = parse_pingzhong_history(text)
    assert frame["累计净值"].isna().all()
    assert frame["单位净值"].iloc[0] == 1.2


def test_period_returns_use_wealth_endpoints_not_compounded_cumulative_changes():
    result = calculate_period_returns(
        ["2026-10-09", "2026-10-12", "2026-10-13", "2026-10-14"], [1.0, 1.01, 1.02, 1.03],
    )
    assert result["returns"]["d3"] == pytest.approx(3.0)
    assert result["returns"]["d7"] is None
    assert result["return_period_dates"]["d3"] == {"from": "2026-10-09", "to": "2026-10-14"}
    assert result["period_basis"] == "calendar_ending_at_last_observation"


def test_month_period_is_calendar_month_not_ninety_nav_rows():
    result = calculate_period_returns(["2026-07-13", "2026-07-14", "2026-10-14"], [1.0, 1.1, 1.21])
    assert result["returns"]["m3"] == pytest.approx(10.0)
    assert result["return_period_dates"]["m3"]["from"] == "2026-07-14"
    assert result["returns"]["y1"] is None


def test_compare_service_exposes_deterministic_period_returns(monkeypatch):
    import pandas as pd
    from app.services.fund_service import FundService
    service = FundService()
    frame = normalize_nav_history(pd.DataFrame([
        {"净值日期": "2026-10-09", "单位净值": 1.0, "provider_change_pct": 0},
        {"净值日期": "2026-10-12", "单位净值": 0.81, "provider_change_pct": 1},
        {"净值日期": "2026-10-13", "单位净值": 0.82, "provider_change_pct": 1},
        {"净值日期": "2026-10-14", "单位净值": 0.83, "provider_change_pct": 1},
    ]))
    monkeypatch.setattr(service, "get_historical_nav", lambda *args: frame)
    monkeypatch.setattr(service, "get_fund_name", lambda code: "测试基金")
    fund = service.get_compare_data(["161725"], range_str="ALL", include_benchmark=False)["funds"][0]
    assert fund["returns"]["d3"] == pytest.approx((1.01 ** 3 - 1) * 100)
    assert fund["return_basis"] == "provider_daily_growth"


def test_compare_chart_window_does_not_limit_period_statistical_history(monkeypatch):
    import pandas as pd
    from app.services import fund_service as service_module
    service = service_module.FundService()
    full = normalize_nav_history(pd.DataFrame([
        {"净值日期": "2025-10-14", "单位净值": 1.0, "provider_change_pct": 0},
        {"净值日期": "2026-10-09", "单位净值": 1.1, "provider_change_pct": 10},
        {"净值日期": "2026-10-14", "单位净值": 1.21, "provider_change_pct": 10},
    ]))
    requested_days = []
    monkeypatch.setattr(service_module, "shanghai_now", lambda: pd.Timestamp("2026-10-14", tz="Asia/Shanghai"))
    monkeypatch.setattr(service, "get_fund_name", lambda code: "测试基金")
    def history(code, days):
        requested_days.append(days)
        return full
    monkeypatch.setattr(service, "get_historical_nav", history)
    fund = service.get_compare_data(["161725"], range_str="1W", include_benchmark=False)["funds"][0]
    assert requested_days == [0]
    assert fund["dates"] == ["2026-10-09", "2026-10-14"]
    assert fund["returns"]["y1"] == pytest.approx(21.0)
    assert fund["return_period_dates"]["y1"]["from"] == "2025-10-14"


def test_lsjz_fallback_is_paged_timed_and_does_not_use_money_yield(monkeypatch):
    from types import SimpleNamespace
    from app.services.fund_service import FundService
    from app.config import settings
    service = FundService()
    calls = []

    def get(url, **kwargs):
        calls.append(kwargs)
        page = kwargs["params"]["pageIndex"]
        rows = [{"FSRQ": "2026-10-13" if page == 1 else "2026-10-12",
                 "DWJZ": "0.5338", "LJJZ": "2.2499", "JZZZL": "0.53"}]
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {
            "Data": {"FundType": "001", "LSJZList": rows}, "TotalCount": 2,
        })

    monkeypatch.setattr(service.session, "get", get)
    frame = service._get_historical_from_lsjz("161725", 30)
    assert len(frame) == 2
    assert frame["单位净值"].iloc[-1] == 0.5338
    assert frame["累计净值"].iloc[-1] == 2.2499
    assert [call["params"]["pageIndex"] for call in calls] == [1, 2]
    assert all(call["timeout"] == settings.REQUEST_TIMEOUT for call in calls)
    assert "startDate" in calls[0]["params"]
    assert calls[0]["params"]["pageSize"] == 100
    monkeypatch.setattr(service.session, "get", lambda *a, **kw: SimpleNamespace(
        raise_for_status=lambda: None,
        json=lambda: {"Data": {"FundType": "005", "LSJZList": [{"DWJZ": "0.2241"}]}, "TotalCount": 1},
    ))
    assert service._get_historical_from_lsjz("000198", 30).empty


@pytest.mark.asyncio
async def test_persistence_and_local_chart_keep_unit_nav_and_source_growth(db_session):
    import pandas as pd
    from app.models.fund import FundNavHistory
    from app.services.history_service import HistoryService
    service = HistoryService()
    frame = normalize_nav_history(pd.DataFrame([
        {"净值日期": "2026-10-12", "单位净值": 1.0, "累计净值": 2.0, "provider_change_pct": 0},
        {"净值日期": "2026-10-13", "单位净值": 0.81, "累计净值": 2.01, "provider_change_pct": 1},
    ]))
    await service._store_to_db("888888", frame)
    local = await service._get_local_data("888888", 0)
    assert local["dates"] == ["2026-10-12", "2026-10-13"]
    assert local["value_basis"] == "unit_nav"
    assert list(map(float, local["values"])) == [1.0, 0.81]
    assert list(map(float, local["changes"])) == [0.0, 1.0]
    row = db_session.query(FundNavHistory).filter_by(fund_code="888888").order_by(FundNavHistory.nav_date.desc()).first()
    assert float(row.accum_nav) == 2.01
