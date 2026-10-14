from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.core import data_contract
from app.core import data_source


def response(rows):
    return SimpleNamespace(
        status_code=200,
        raise_for_status=lambda: None,
        json=lambda: {"success": True, "errorCode": 0, "data": rows},
    )


def test_tiantian_uses_current_batch_contract_and_retains_nav(monkeypatch):
    adapter = data_source.EastmoneyDirectAdapter()
    calls = []
    now = datetime(2026, 10, 13, 14, 30, tzinfo=timezone(timedelta(hours=8)))
    monkeypatch.setattr(data_contract, "shanghai_now", lambda: now)

    def post(url, **kwargs):
        calls.append((url, kwargs))
        return response([
            {"FCODE": "161725", "SHORTNAME": "招商中证白酒指数(LOF)A",
             "GSZ": 0.5294, "GSZZL": 0, "GZTIME": now.strftime("%Y-%m-%d %H:%M"),
             "NAV": 0.5338, "PDATE": (now - timedelta(days=1)).date().isoformat(),
             "NAVCHGRT": 0.53, "FUNDTYPE": "001"},
            {"FCODE": "015916", "SHORTNAME": "永赢医药创新智选混合发起C",
             "GSZ": None, "GSZZL": None, "GZTIME": None, "NAV": 1.6017,
             "PDATE": (now - timedelta(days=1)).date().isoformat(),
             "NAVCHGRT": -0.85, "FUNDTYPE": "002"},
        ])

    monkeypatch.setattr(adapter.session, "post", post)
    results = adapter.fetch_tiantian_batch(["161725", "015916"])
    assert len(calls) == 1
    assert calls[0][0].endswith("/mm/newCore/FundValuationLast")
    assert calls[0][1]["data"]["FCODES"] == "161725,015916"
    assert "params" not in calls[0][1]
    assert results[0].nav == 0.5294
    assert results[0].change_pct == 0
    assert results[0].previous_nav == 0.5338
    assert results[1].nav == 1.6017
    assert results[1].change_pct == -0.85
    assert results[1].data_kind == "latest_nav"


def test_tiantian_failure_does_not_retry_get_or_mirror(monkeypatch):
    adapter = data_source.EastmoneyDirectAdapter()
    calls = []

    def post(url, **kwargs):
        calls.append(url)
        raise data_source.requests.Timeout()

    monkeypatch.setattr(adapter.session, "post", post)
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: pytest.fail("No duplicate GET request"))
    assert not adapter.fetch_tiantian_batch(["015916"])[0].is_success
    assert calls == [adapter.TIANTIAN_URL]


def test_money_fund_yield_is_never_a_unit_nav(monkeypatch):
    adapter = data_source.EastmoneyDirectAdapter()
    monkeypatch.setattr(adapter.session, "post", lambda *a, **kw: response([
        {"FCODE": "000198", "SHORTNAME": "天弘余额宝货币", "NAV": 0.2241,
         "PDATE": "2026-10-12", "GSZ": None, "FUNDTYPE": "005"}
    ]))
    result = adapter.fetch_tiantian_batch(["000198"])[0]
    assert not result.is_success
    assert result.nav is None
    assert result.fund_type == "money_market"


def test_estimate_freshness_checks_date_age_and_lunch_break():
    tz = timezone(timedelta(hours=8))
    now = datetime(2026, 10, 13, 14, 30, tzinfo=tz)
    assert data_source.is_current_estimate("2026-10-13 14:29", now=now)
    assert not data_source.is_current_estimate("2026-10-12 14:29", now=now)
    assert not data_source.is_current_estimate("2026-10-13 13:00", now=now)
    assert not data_source.is_current_estimate("2026-10-13 14:40", now=now)
    assert data_source.is_current_estimate(
        "2026-10-13 11:30", now=now.replace(hour=12, minute=30)
    )
    assert not data_source.is_current_estimate(
        "2026-10-13 15:00", now=now.replace(hour=15, minute=30), close_hour=16
    )


def test_mobile_reads_unit_nav_not_accumulated_nav(monkeypatch):
    adapter = data_source.EastmoneyDirectAdapter()
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: SimpleNamespace(
        raise_for_status=lambda: None,
        json=lambda: {"Success": True, "Datas": [
            {"FCODE": "161725", "SHORTNAME": "招商中证白酒指数(LOF)A",
             "NAV": "0.5338", "ACCNAV": "2.2499", "PDATE": "2026-10-12", "NAVCHGRT": "0.53"}
        ]},
    ))
    row = adapter.fetch_mobile_batch(["161725"])[0]
    assert row.nav == 0.5338
    assert row.accumulated_nav == 2.2499


def test_lsjz_money_yield_is_not_used_if_primary_is_down(monkeypatch):
    adapter = data_source.EastmoneyDirectAdapter()
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: SimpleNamespace(
        raise_for_status=lambda: None,
        json=lambda: {"Data": {"FundType": "005", "LSJZList": [{"DWJZ": "0.2241", "FSRQ": "2026-10-12"}]}},
    ))
    result = adapter._try_eastmoney_lsjz("000198")
    assert not result.is_success
    assert result.fund_type == "money_market"


@pytest.mark.asyncio
async def test_single_and_batch_share_one_primary_request(monkeypatch, source_manager):
    manager = source_manager
    calls = []

    def fetch(codes):
        calls.append(codes)
        return [data_source.FundDataResult(code=c, name="基金", nav=1.2,
                                          update_time="2026-10-12", source="tiantian", data_kind="latest_nav")
                for c in codes]

    monkeypatch.setattr(manager._eastmoney, "fetch_tiantian_batch", fetch)
    monkeypatch.setattr(manager._sina, "fetch_batch", lambda codes: [
        data_source.FundDataResult(code=c, source="sina", error="no estimate") for c in codes
    ])
    rows = await manager.fetch_batch(["015916", "161725", "015916"])
    assert [r.code for r in rows] == ["015916", "161725", "015916"]
    assert calls == [["015916", "161725"]]
    single = await manager.fetch_single("015916")
    assert single.nav == rows[0].nav
    assert calls == [["015916", "161725"]]

