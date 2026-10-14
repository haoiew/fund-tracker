"""Production parsers follow the providers' own field contracts, never synthetic runtime fallbacks."""
from datetime import datetime
from types import SimpleNamespace

import pytest

from app.core import data_contract
from app.core import data_source


@pytest.fixture(autouse=True)
def now(monkeypatch):
    monkeypatch.setattr(data_contract, "shanghai_now", lambda: datetime(2026, 10, 14, 15, 5, tzinfo=data_source.SHANGHAI))


DAYFUND = "2026-10-13|1.5845|1.5845|-0.0172|-1.09%|-1.80%|-0.0285|1.5560|1.6017|2026-10-14|15:00"


def test_dayfund_reads_estimate_and_unit_nav_as_separate_fields():
    row = data_source.DayfundAdapter.parse_response("015916", DAYFUND)
    assert row.is_realtime and row.nav == 1.5560 and row.change_pct == -1.80
    assert row.previous_nav == 1.5845 and row.previous_nav_date == "2026-10-13"
    assert row.daily_change == -1.09 and row.accumulated_nav == 1.5845


@pytest.mark.parametrize("body", ["<html>HTTP 200</html>", DAYFUND.replace("15:00", "09:15"),
                                  DAYFUND.replace("1.5560", "NaN"), DAYFUND.replace("-1.80%", "-100%"),
                                  DAYFUND.replace("1.5560", "2.5560")])
def test_dayfund_invalid_or_stale_data_is_not_a_current_estimate(body):
    row = data_source.DayfundAdapter.parse_response("015916", body)
    assert not row.is_realtime and not row.is_success and row.error


def point(hour, minute, nav="1.55588848", growth="-0.01805713"):
    stamp = int(datetime(2026, 10, 14, hour, minute, tzinfo=data_source.SHANGHAI).timestamp() * 1000)
    return {"time": stamp, "forecastNetValue": nav, "forecastGrowth": growth}


def test_fund123_converts_fraction_to_percent_and_chooses_latest_time_not_last_row():
    payload = {"success": True, "list": [point(15, 0), point(14, 55)]}
    row = data_source.Fund123Adapter.parse_response("015916", payload, "1.5845")
    assert row.is_realtime and row.nav == 1.55588848
    assert row.change_pct == pytest.approx(-1.805713)
    assert row.update_time == "2026-10-14T15:00:00+08:00"
    assert row.previous_nav is None and row.previous_nav_date is None  # MM-DD does not establish a publication year.


@pytest.mark.parametrize("payload", [{"success": True, "list": []}, {"success": False, "list": [point(15, 0)]},
                                     {"success": True, "list": [point(9, 15)]},
                                     {"success": True, "list": [point(15, 0, growth="NaN")]},
                                     {"success": True, "list": "not a list"}])
def test_fund123_empty_invalid_or_stale_series_do_not_become_estimates(payload):
    row = data_source.Fund123Adapter.parse_response("015916", payload)
    assert not row.is_realtime and row.error


def test_fund123_reuses_anonymous_context_and_never_exposes_csrf_in_errors(monkeypatch):
    calls = []
    token = "test-only-csrf"

    def get(*args, **kwargs):
        calls.append("profile")
        return SimpleNamespace(raise_for_status=lambda: None,
                               text=f'{{"csrf":"{token}","productId":"public-product","netValue":"1.5845"}}')

    def post(url, **kwargs):
        calls.append("estimate")
        assert kwargs["params"] == {"_csrf": token}
        assert kwargs["json"]["startTime"] == "2026-10-14"
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"success": True, "list": [point(15, 0)]})

    session = data_source.requests.Session()
    monkeypatch.setattr(session, "get", get)
    monkeypatch.setattr(session, "post", post)
    monkeypatch.setattr(data_source.requests, "Session", lambda: session)
    adapter = data_source.Fund123Adapter()
    try:
        assert adapter.fetch_single("015916").is_realtime
        assert adapter.fetch_single("015916").is_realtime
        assert calls == ["profile", "estimate", "estimate"]

        def fail(*args, **kwargs):
            raise data_source.requests.HTTPError(f"https://example.invalid/?_csrf={token}")

        monkeypatch.setattr(session, "post", fail)
        row = adapter.fetch_single("015916")
        assert row.error == "数米估值请求失败: HTTPError" and token not in str(row)
        assert not adapter._contexts  # Re-bootstrap normally on the next refresh, no retry chain.
    finally:
        adapter.close()
