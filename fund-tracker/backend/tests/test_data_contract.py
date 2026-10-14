"""Contract/normalization fixtures are isolated here; production never fabricates data."""
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.core import data_contract as contract, data_source, provider_normalizers as normalizers
from app.schemas.fund import FundRealtimeData
from app.services.fund_service import get_fund_service


@pytest.fixture
def now(monkeypatch):
    value = datetime(2026, 10, 14, 14, 5, tzinfo=contract.SHANGHAI)
    monkeypatch.setattr(contract, "shanghai_now", lambda: value)
    return value


def quality(**overrides):
    kwargs = dict(source="sina", data_kind="realtime_estimate", source_time="2026-10-14 14:04",
                  nav_date="2026-10-13", nav_source="tiantian", fetched_at="2026-10-14T14:05:00+08:00",
                  available=True, is_realtime=True)
    kwargs.update(overrides)
    return contract.describe_quote_quality(**kwargs)


def test_provider_catalog_declares_shared_upstreams_native_units_and_capabilities():
    catalog = contract.get_provider_catalog()
    assert catalog["contract_version"] == "1.0"
    providers = {item["source"]: item for item in catalog["providers"]}
    assert len(providers) == 8
    assert {providers[source]["upstream_family"] for source in ("tiantian", "eastmoney_mobile", "eastmoney_lsjz", "pingzhongdata")} == {"eastmoney"}
    assert providers["fund123"]["native_change_unit"] == "ratio"
    assert providers["fund123"]["change_unit"] == "percent"
    assert providers["dayfund"]["upstream_family"] is None
    assert providers["sina"]["supports_batch"]
    assert providers["tencent"]["data_kinds"] == ("latest_nav",)
    assert data_source.FundDataResult is contract.FundDataResult


def test_provider_quality_distinguishes_source_baseline_and_fetch_time(now):
    result = quality()
    assert result.value_source == "sina"
    assert result.nav_source == "tiantian"
    assert result.source_time != result.fetched_at
    assert result.price_basis == "provider_estimate"
    assert result.price_unit == "per_share" and result.currency is None
    assert result.freshness == "current_estimate"
    assert result.assessed_at == now.isoformat()
    assert "provider_estimate" in {item.code for item in result.warnings}


def test_official_nav_quality_uses_actual_nav_source_and_not_realtime(now):
    result = quality(data_kind="latest_nav", is_realtime=False)
    assert result.value_source == "tiantian"
    assert result.upstream_family == "eastmoney"
    assert result.freshness == "dated_nav"
    assert result.price_basis == "unit_nav"


def test_missing_money_pending_and_inferred_quotes_are_not_conflated(now):
    missing = quality(available=False, data_kind="unavailable")
    assert missing.availability == "unavailable" and missing.value_source is None
    assert quality(available=False, fund_type="money_market").availability == "unsupported"
    pending = quality(available=False, data_kind="unavailable", pending_sources=["sina"])
    assert pending.availability == "pending"
    assert pending.pending_sources == ("sina",)
    inferred = quality(source="holdings_estimate", data_kind="holdings_estimate", is_realtime=False, is_inferred=True)
    assert inferred.freshness == "current_reference"
    assert inferred.price_basis == "inferred_unit_nav"
    assert "inferred_quote" in {item.code for item in inferred.warnings}


def test_quality_dates_use_shanghai_and_do_not_invent_currency_or_nav_day(now):
    result = quality(nav_date=None, nav_source=None)
    assert result.nav_date is None and result.currency is None
    assert "missing_nav_date" in {item.code for item in result.warnings}
    same_day = quality(nav_date="2026-10-14", now=datetime(2026, 10, 13, 20, tzinfo=timezone.utc))
    assert same_day.nav_age_calendar_days == 0
    future = quality(nav_date="2026-10-15")
    assert future.nav_age_calendar_days is None
    assert "invalid_nav_date" in {item.code for item in future.warnings}


def test_normalizers_have_no_network_and_never_price_with_accumulated_nav(now, monkeypatch):
    import requests
    monkeypatch.setattr(requests.Session, "request", lambda *a, **k: pytest.fail("normalization must not perform HTTP"))
    row = normalizers.normalize_eastmoney_nav({"FCODE": "015916", "NAV": "1.5", "ACCNAV": "4.5", "PDATE": "2026-10-13"}, "eastmoney_mobile")
    assert row.nav == 1.5 and row.accumulated_nav == 4.5
    assert contract._number(True) is None
    points = {"success": True, "list": [{"forecastNetValue": "1.515", "forecastGrowth": ".01", "time": int(now.timestamp() * 1000)}]}
    estimate = normalizers.normalize_fund123("015916", points, 1.5)
    assert estimate.change_pct == 1.0
    assert estimate.previous_nav_date is None


def test_source_selection_retains_separate_official_nav_provenance(now):
    snapshot = {source: contract.FundDataResult(code="015916", source=source, error="test missing") for source, _ in contract.DATA_SOURCE_COMPARISON_SOURCES}
    snapshot["sina"] = contract.FundDataResult(code="015916", source="sina", nav=1.515, change_pct=1, update_time="2026-10-14 14:04", data_kind="realtime_estimate")
    snapshot["tiantian"] = contract.FundDataResult(code="015916", source="tiantian", nav=1.5, update_time="2026-10-13", data_kind="latest_nav")
    normalized = data_source.DataSourceManager._normalize_snapshot("015916", snapshot)
    selected = data_source.DataSourceManager._select_result("015916", normalized)
    assert selected.source == "sina" and selected.previous_nav_source == "tiantian"
    assert selected.nav == 1.515 and selected.previous_nav == 1.5


@pytest.mark.asyncio
async def test_display_policy_rebuilds_quality_after_nav_or_unavailable_selection(now, monkeypatch):
    service = get_fund_service()
    direct = FundRealtimeData(code="015916", name="基金", estimate_nav=Decimal("1.515"), estimate_change=Decimal("1"),
                              update_time="2026-10-14 14:04", data_source="sina", data_kind="realtime_estimate", is_realtime=True,
                              official_nav=Decimal("1.5"), official_update_time="2026-10-13", official_nav_source="tiantian")
    provider = await service._select_display_quote(direct, "provider")
    nav = await service._select_display_quote(direct, "nav")
    assert provider.quality.price_basis == "provider_estimate"
    assert nav.quality.price_basis == "unit_nav" and nav.quality.value_source == "tiantian"
    unavailable = await service._select_display_quote(direct.model_copy(update={"is_realtime": False}), "provider")
    assert unavailable.estimate_nav is None
    assert unavailable.quality.availability == "unavailable"
    assert asdict(nav.quality)["nav_date"] == "2026-10-13"


def test_static_provider_api_does_not_query_external_services(client, monkeypatch):
    monkeypatch.setattr(data_source.DataSourceManager, "fetch_batch", lambda *a, **k: pytest.fail("catalog must not collect"))
    response = client.get("/api/v1/funds/providers")
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["contract_version"] == "1.0"
    assert len(payload["providers"]) == 8


def test_quality_is_json_serializable_in_the_public_schema(now):
    result = FundRealtimeData(code="015916", name="基金", quality=quality())
    dumped = result.model_dump(mode="json")
    assert dumped["quality"]["change_unit"] == "percent"
    assert isinstance(dumped["quality"]["warnings"], list)


def test_missing_timestamp_never_gets_a_current_quality_label(now):
    assert quality(source_time=None, is_realtime=True).freshness == "stale"


def test_realtime_http_response_includes_quality_from_selected_policy(client, now, monkeypatch):
    from types import SimpleNamespace
    from app.api.v1 import funds
    service = get_fund_service()
    direct = FundRealtimeData(code="015916", name="测试基金", estimate_nav=Decimal("1.515"),
                              update_time="2026-10-14 14:04", data_source="sina", data_kind="realtime_estimate", is_realtime=True,
                              official_nav=Decimal("1.5"), official_update_time="2026-10-13", official_nav_source="tiantian")
    async def read_quote(code, view="auto", refresh=False):
        return await service._select_display_quote(direct, view)
    monkeypatch.setattr(funds, "get_fund_service", lambda: SimpleNamespace(get_realtime_data=read_quote))
    response = client.get("/api/v1/funds/realtime/015916?view=nav")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["quality"]["price_basis"] == "unit_nav"
    assert data["quality"]["value_source"] == "tiantian"
    assert data["quality"]["currency"] is None
