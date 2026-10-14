"""Sina's own quotes/index.js uses fu[2], fu[6], fu[7] + fu[1]."""
from datetime import datetime
from types import SimpleNamespace

import pytest

from app.core import data_contract
from app.core import data_source


# Public upstream snapshot, 2026-10-14 14:00 Shanghai. No runtime fixtures.
SINA_MEDICINE = (
    'var hq_str_f_015916="永赢医药创新智选混合发起C,1.5845,1.5845,1.6017,2026-10-13,29.407";\n'
    'var hq_str_fu_015916="永赢医药创新智选混合发起C,14:00:00,1.5392,1.5845,1.5845,0,-2.8601,2026-10-14,1.5537,-1.9446";'
)


@pytest.fixture
def now(monkeypatch):
    stamp = datetime(2026, 10, 14, 14, 5, tzinfo=data_source.SHANGHAI)
    monkeypatch.setattr(data_contract, "shanghai_now", lambda: stamp)
    return stamp


def fake_response(body):
    return SimpleNamespace(text=body, raise_for_status=lambda: None)


def test_sina_uses_its_own_page_field_mapping_not_second_estimate(monkeypatch, now):
    adapter = data_source.SinaFundAdapter()
    calls = []

    def get(url, **kwargs):
        calls.append((url, kwargs))
        return fake_response(SINA_MEDICINE)

    monkeypatch.setattr(adapter.session, "get", get)
    row = adapter.fetch_batch(["015916", "015916"])[0]
    assert len(calls) == 1
    assert calls[0][0] == "https://hq.sinajs.cn/list=f_015916,fu_015916"
    prepared = data_source.requests.Request("GET", calls[0][0], params=calls[0][1].get("params")).prepare()
    assert "%2C" not in prepared.url  # Upstream treats encoded commas as one nonexistent symbol.
    assert "finance.sina.com.cn" in adapter.session.headers["Referer"]
    assert row.is_success and row.is_realtime
    assert row.source == "sina" and row.data_kind == "realtime_estimate"
    assert row.nav == 1.5392 and row.change_pct == -2.8601
    assert row.update_time == "2026-10-14 14:00:00"
    assert row.previous_nav == 1.5845 and row.previous_nav_date == "2026-10-13"
    assert row.accumulated_nav == 1.5845
    assert row.daily_change is None  # Unit-NAV ratio is not a published dividend-adjusted daily return.


@pytest.mark.parametrize("body", [
    SINA_MEDICINE.replace("14:00:00", "13:00:00"),
    SINA_MEDICINE.replace("14:00:00", "14:20:00"),
    SINA_MEDICINE.replace("2026-10-14,", "2026-10-13,"),
    SINA_MEDICINE.replace("14:00:00", ""),
    SINA_MEDICINE.replace("1.5392", "NaN"),
    SINA_MEDICINE.replace("-2.8601", "-100"),
    SINA_MEDICINE.replace("1.5392", "2.5845"),
    SINA_MEDICINE.replace("永赢医药创新智选混合发起C", "测试货币基金"),
    'var hq_str_f_015916=""; var hq_str_fu_015916="";',
    SINA_MEDICINE.replace("hq_str_fu_015916", "hq_str_fu_018125"),
    '<html>200 is not a quote</html>',
])
def test_sina_invalid_or_stale_payload_is_not_a_current_quote(monkeypatch, now, body):
    adapter = data_source.SinaFundAdapter()
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: fake_response(body))
    row = adapter.fetch_batch(["015916"])[0]
    assert not row.is_success and not row.is_realtime
    assert row.nav is None and row.error


def test_sina_does_not_invent_official_publication_date(monkeypatch, now):
    adapter = data_source.SinaFundAdapter()
    body = SINA_MEDICINE.replace("1.6017,2026-10-13", "1.6017,2026-10-15")
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: fake_response(body))
    row = adapter.fetch_batch(["015916"])[0]
    assert row.is_realtime
    assert row.previous_nav is None and row.previous_nav_date is None


def test_sina_batches_and_handles_timeout_without_losing_codes(monkeypatch, now):
    adapter = data_source.SinaFundAdapter()
    calls = []

    def get(url, **kwargs):
        calls.append(url)
        raise data_source.requests.Timeout()

    monkeypatch.setattr(adapter.session, "get", get)
    codes = [f"{c:06d}" for c in range(101)]
    assert adapter.fetch_batch([]) == []
    rows = adapter.fetch_batch(codes)
    assert len(calls) == 2
    assert [r.code for r in rows] == codes
    assert all(not r.is_success and "Timeout" in r.error for r in rows)


@pytest.mark.asyncio
async def test_manager_queries_sina_for_all_codes_and_preserves_nav_when_estimate_missing(monkeypatch, now, source_manager):
    manager = source_manager
    calls = []
    primary = [
        data_source.FundDataResult(code="012414", nav=.5266, source="tiantian", data_kind="realtime_estimate",
                                   update_time="2026-10-14 14:00", previous_nav=.5258, previous_nav_date="2026-10-13"),
        data_source.FundDataResult(code="015916", nav=1.5845, source="tiantian", data_kind="latest_nav",
                                   update_time="2026-10-13", previous_nav=1.5845, previous_nav_date="2026-10-13", daily_change=-1.07),
        data_source.FundDataResult(code="018125", nav=1.6858, source="tiantian", data_kind="latest_nav",
                                   update_time="2026-10-13", previous_nav=1.6858, previous_nav_date="2026-10-13"),
        data_source.FundDataResult(code="000198", source="tiantian", fund_type="money_market", error="not a price"),
    ]
    monkeypatch.setattr(manager._eastmoney, "fetch_tiantian_batch", lambda codes: primary)

    def sina(codes):
        calls.append(codes)
        return [
            data_source.FundDataResult(code="015916", nav=1.5392, change_pct=-2.8601, source="sina",
                                       data_kind="realtime_estimate", update_time="2026-10-14 14:00",
                                       previous_nav=1.5845, previous_nav_date="2026-10-13"),
            data_source.FundDataResult(code="018125", source="sina", error="missing estimate"),
        ]

    monkeypatch.setattr(manager._sina, "fetch_batch", sina)
    rows = await manager.fetch_batch(["012414", "015916", "018125", "000198"])
    assert calls == [["012414", "015916", "018125", "000198"]]
    assert [r.source for r in rows] == ["tiantian", "sina", "tiantian", "tiantian"]
    assert rows[1].daily_change == -1.07  # Keep the authoritative NAV metadata.
    assert rows[2].nav == 1.6858  # Failed estimate cannot discard valid unit NAV.


@pytest.mark.asyncio
async def test_manager_keeps_newer_official_nav_for_after_close_selection(monkeypatch, now, source_manager):
    from app.core.quote_policy import select_quote
    from app.services.fund_service import FundService

    now = now.replace(hour=16)
    monkeypatch.setattr(data_contract, "shanghai_now", lambda: now)
    manager = source_manager
    primary = data_source.FundDataResult(code="015916", nav=1.55, source="tiantian", data_kind="latest_nav",
                                        update_time="2026-10-14", previous_nav=1.55,
                                        previous_nav_date="2026-10-14", daily_change=-2.17)
    sina = data_source.FundDataResult(code="015916", nav=1.5392, source="sina", data_kind="realtime_estimate",
                                     update_time="2026-10-14 15:00", previous_nav=1.5845, previous_nav_date="2026-10-13")
    monkeypatch.setattr(manager._eastmoney, "fetch_tiantian_batch", lambda codes: [primary])
    monkeypatch.setattr(manager._sina, "fetch_batch", lambda codes: [sina])
    row = (await manager.fetch_batch(["015916"]))[0]
    direct = FundService()._build_realtime_response("015916", "基金", row)
    selected = select_quote(direct, now=now)
    assert row.previous_nav == 1.55 and row.previous_nav_date == "2026-10-14"
    assert float(selected.estimate_nav) == 1.55
    assert float(selected.official_change) == pytest.approx(-2.17)
    assert selected.data_kind == "latest_nav"


@pytest.mark.asyncio
async def test_manager_rejects_same_date_unit_nav_conflict(monkeypatch, now, source_manager):
    manager = source_manager
    primary = data_source.FundDataResult(code="015916", nav=1.5845, source="tiantian", data_kind="latest_nav",
                                        update_time="2026-10-13", previous_nav=1.5845, previous_nav_date="2026-10-13")
    wrong = data_source.FundDataResult(code="015916", nav=1.05, source="sina", data_kind="realtime_estimate",
                                      update_time="2026-10-14 14:00", previous_nav=1.1, previous_nav_date="2026-10-13")
    monkeypatch.setattr(manager._eastmoney, "fetch_tiantian_batch", lambda codes: [primary])
    monkeypatch.setattr(manager._sina, "fetch_batch", lambda codes: [wrong])
    row = (await manager.fetch_batch(["015916"]))[0]
    assert row.source == "tiantian" and row.nav == 1.5845
    assert row.stale_reason and "净值" in row.stale_reason


@pytest.mark.asyncio
async def test_current_tiantian_still_requests_sina_and_uses_its_priority(monkeypatch, now, source_manager):
    manager = source_manager
    primary = data_source.FundDataResult(code="012414", nav=.5266, source="tiantian", data_kind="realtime_estimate",
                                        update_time="2026-10-14 14:00")
    monkeypatch.setattr(manager._eastmoney, "fetch_tiantian_batch", lambda codes: [primary])

    calls = []

    def sina(codes):
        calls.append(codes)
        return [data_source.FundDataResult(code=code, nav=.5267, source="sina", data_kind="realtime_estimate",
                                           update_time="2026-10-14 14:00") for code in codes]

    monkeypatch.setattr(manager._sina, "fetch_batch", sina)
    assert (await manager.fetch_batch(["012414"]))[0].source == "sina"
    assert calls == [["012414"]]


@pytest.mark.asyncio
async def test_source_comparison_exposes_realtime_coverage_not_just_nav_availability(monkeypatch):
    from app.services.fund_service import FundService

    service = FundService()

    async def compare(code, wait_all=True):
        return {"sources": [{"source": "sina", "name": "基金"}], "best_source": "sina",
                "best_source_display_name": "新浪基金估值", "total_sources": 6, "realtime_sources": 1}

    monkeypatch.setattr(service, "_data_source", SimpleNamespace(compare_sources=compare))
    result = await service.get_data_source_comparison("015916")
    assert result["realtime_sources"] == 1 and result["total_sources"] == 6


@pytest.mark.asyncio
async def test_source_comparison_rejects_conflicting_sina_like_default_selection(monkeypatch, now, source_manager):
    manager = source_manager
    primary = data_source.FundDataResult(code="015916", nav=1.5845, source="tiantian", data_kind="latest_nav",
                                        update_time="2026-10-13", previous_nav=1.5845, previous_nav_date="2026-10-13")
    wrong = data_source.FundDataResult(code="015916", nav=1.05, source="sina", data_kind="realtime_estimate",
                                      update_time="2026-10-14 14:00", previous_nav=1.1, previous_nav_date="2026-10-13")
    fail = lambda code: data_source.FundDataResult(code=code, source="unknown", error="test unavailable")
    monkeypatch.setattr(manager._eastmoney, "fetch_tiantian_batch", lambda codes: [primary])
    monkeypatch.setattr(manager._sina, "fetch_batch", lambda codes: [wrong])
    monkeypatch.setattr(manager._eastmoney, "fetch_mobile_batch", lambda codes: [fail(c) for c in codes])
    for method in ("_try_tencent", "_try_eastmoney_lsjz", "_try_pingzhongdata"):
        monkeypatch.setattr(manager._eastmoney, method, fail)
    result = await manager.compare_sources("015916")
    row = next(r for r in result["sources"] if r["source"] == "sina")
    assert not row["is_available"] and not row["is_realtime"]
    assert row["error"] and "净值" in row["error"]
    assert result["best_source"] == "tiantian" and result["realtime_sources"] == 0
