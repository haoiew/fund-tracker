from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.core.quote_policy import select_quote
from app.schemas.fund import FundRealtimeData

NOW = datetime(2026, 10, 13, 14, 30, tzinfo=timezone(timedelta(hours=8)))


def direct(**kwargs):
    values = dict(code="015916", name="基金", estimate_nav=Decimal("1.6"),
                  estimate_change=Decimal("-0.85"), update_time="2026-10-12",
                  data_kind="latest_nav", official_nav=Decimal("1.6"),
                  official_change=Decimal("-0.85"), official_update_time="2026-10-12")
    values.update(kwargs)
    return FundRealtimeData(**values)


def test_intraday_prefers_provider_estimate_over_inference():
    row = direct(data_kind="realtime_estimate", is_realtime=True,
                 estimate_nav=Decimal("1.61"), update_time="2026-10-13 14:29")
    assert select_quote(row, now=NOW).estimate_nav == Decimal("1.61")


def test_missing_provider_estimate_uses_real_quote_inference_and_correct_base():
    inferred = {"holdings_based_estimate": {
        "feasible": True, "weighted_stock_change_pct": 2.5,
        "update_time": "2026-10-13 14:29", "quoted_weight_coverage": 0.9,
        "quoted_nav_weight_pct": 40.0, "position_date": "2026-06-30",
    }}
    row = select_quote(direct(), inferred, now=NOW)
    assert row.estimate_nav == Decimal("1.6400")
    assert row.is_inferred and not row.is_realtime
    assert row.update_time == "2026-10-13 14:29"
    assert row.official_nav == Decimal("1.6")
    assert row.estimation_details["quoted_nav_weight_pct"] == 40.0


def test_old_nav_is_manual_only_when_no_estimate():
    auto = select_quote(direct(), now=NOW)
    assert auto.estimate_nav is None
    assert auto.official_nav == Decimal("1.6")
    assert select_quote(direct(), view="nav", now=NOW).estimate_nav == Decimal("1.6")


def test_nav_automatically_shown_only_after_close_and_today_publication():
    today = direct(official_update_time="2026-10-13", update_time="2026-10-13")
    assert select_quote(today, now=NOW).estimate_nav is None
    assert select_quote(today, now=NOW.replace(hour=18)).data_kind == "latest_nav"
    assert select_quote(direct(), now=NOW.replace(hour=18)).estimate_nav is None


def test_stale_or_undated_inference_is_not_current():
    for stamp in ("2026-10-12 14:29", None):
        data = {"holdings_based_estimate": {"feasible": True,
                                           "weighted_stock_change_pct": 2.5,
                                           "update_time": stamp}}
        assert select_quote(direct(), data, now=NOW).estimate_nav is None


def test_provider_only_view_does_not_use_inference():
    data = {"holdings_based_estimate": {"feasible": True,
                                       "weighted_stock_change_pct": 2.5,
                                       "update_time": "2026-10-13 14:29"}}
    assert select_quote(direct(), data, view="provider", now=NOW).estimate_nav is None


def test_published_today_nav_does_not_remove_manual_provider_view():
    row = direct(data_kind="realtime_estimate", is_realtime=True,
                 official_update_time="2026-10-13", estimate_nav=Decimal("1.61"),
                 update_time="2026-10-13 15:00")
    after_close = NOW.replace(hour=18)
    assert select_quote(row, now=after_close).estimate_nav == Decimal("1.6")
    assert select_quote(row, view="provider", now=after_close).estimate_nav == Decimal("1.61")


def test_holdings_parser_uses_latest_report_only():
    from app.services.fund_service import FundService
    service = FundService()
    sample = """
    截止至：<font>2026-06-30</font>
    <table><tr><td>1</td><td>600519</td><td>贵州茅台</td><td>4.12%</td></tr></table>
    截止至：<font>2026-03-31</font>
    <table><tr><td>1</td><td>600519</td><td>贵州茅台</td><td>3.00%</td></tr></table>
    """
    result = service._parse_f10_holding_rows(sample, "jjcc")
    assert result["position_date"] == "2026-06-30"
    assert len(result["holdings"]) == 1
    assert result["holdings"][0]["weight"] == 4.12


def test_quote_parser_does_not_replace_missing_percent_with_price_delta(monkeypatch):
    from app.services.fund_service import FundService
    from types import SimpleNamespace
    service = FundService()
    fields = [""] * 34
    fields[1] = "贵州茅台"
    fields[7] = "10"
    fields[30] = "20261013142900"
    fields[31] = "0.2"
    fields[32] = "--"
    monkeypatch.setattr(service.session, "get", lambda *a, **kw: SimpleNamespace(
        status_code=200, text='v_sh600519="' + "~".join(fields) + '";'
    ))
    assert service._fetch_tencent_quotes(["sh600519"]) == {}
