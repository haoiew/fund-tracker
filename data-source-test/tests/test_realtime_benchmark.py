"""Offline regression checks for benchmark units, clocks and statistics."""
from datetime import datetime

import pytest

import evaluate_realtime_sources as benchmark
from app.core import data_contract
from app.core import data_source


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    monkeypatch.setattr(data_contract, "shanghai_now", lambda: datetime(2026, 10, 14, 15, 5, tzinfo=data_source.SHANGHAI))


def test_dayfund_follows_its_own_script_fields_and_keeps_nav_separate():
    row = benchmark.parse_dayfund("015916", "2026-10-13|1.5845|1.5845|-0.0172|-1.09%|-2.57%|-0.0407|1.5438|1.6017|2026-10-14|14:55:00")
    assert row.nav == 1.5438 and row.change_pct == -2.57
    assert row.previous_nav == 1.5845 and row.previous_nav_date == "2026-10-13"
    assert row.is_realtime


@pytest.mark.parametrize("body", ["", "<html>HTTP 200 is not a quote</html>",
    "2026-10-13|1.5845|1.5845|0|0%|-2.57%|0|2.5438|1.6017|2026-10-14|14:55:00"])
def test_dayfund_missing_or_inconsistent_fields_are_not_valid_quotes(body):
    assert not benchmark.parse_dayfund("015916", body).is_success


def test_fund123_growth_is_a_fraction_and_last_point_is_selected_by_time():
    latest = {"time": 1791961200000, "forecastNetValue": "1.55588848", "forecastGrowth": "-0.01805713"}
    row, point = benchmark.parse_fund123("015916", {"success": True, "list": [latest, {**latest, "time": 1791957600000}]}, 1.5845)
    assert point == latest
    assert row.change_pct == pytest.approx(-1.805713)
    assert row.nav == 1.55588848 and row.is_realtime
    assert row.update_time == "2026-10-14T15:00:00+08:00"


def test_empty_or_stale_estimate_series_is_not_current():
    row, _ = benchmark.parse_fund123("015916", {"success": True, "list": []}, 1.5845)
    assert not row.is_success
    row, _ = benchmark.parse_fund123("015916", {"success": True, "list": [
        {"time": 1791957600000, "forecastNetValue": "1.55588848", "forecastGrowth": "-0.01805713"}
    ]}, 1.5845)
    assert row.is_success and not row.is_realtime


def test_latency_percentile_and_snapshot_regression_are_not_hidden():
    assert benchmark.percentile([], 95) is None
    assert benchmark.percentile([10, 20, 30], 50) == 20
    assert benchmark.percentile([10, 20, 30], 95) == 29
    samples = []
    for stamp in ["2026-10-14 15:00", "2026-10-14 14:55", "2026-10-14 15:00"]:
        samples.append({"sources": {"test": {"duration_ms": 10, "http_calls": [
            {"http_status": 200, "business_success": True, "duration_ms": 10}
        ], "quotes": [{"code": "015916", "update_time": stamp, "is_current_estimate": False}]}}})
    result = benchmark.summarize(samples, ["015916"])["test"]
    assert result["http_successes"] == 3
    assert result["fresh_coverage"]["max"] == 0
    assert result["funds"]["015916"]["timestamp_advances"] == 1


def test_actual_quote_age_is_not_reset_by_the_shanghai_close_policy():
    quote = {"data_kind": "realtime_estimate", "update_time": "2026-10-14 14:50:00"}
    assert benchmark.quote_age_seconds(quote, "2026-10-14T15:20:00+08:00") == 1800
    quote["update_time"] = "2026-10-14T06:50:00Z"
    assert benchmark.quote_age_seconds(quote, "2026-10-14T15:20:00+08:00") == 1800
    assert benchmark.quote_age_seconds({"data_kind": "latest_nav", "update_time": "2026-10-13"}, "2026-10-14 15:20") is None


def test_same_time_different_prices_are_reported_as_observations():
    rounds = [{"sources": {"test": {"duration_ms": 1, "http_calls": [], "quotes": [{
        "code": "015916", "data_kind": "realtime_estimate", "update_time": "2026-10-14 15:00", "nav": nav
    }]}}} for nav in (1.55, 1.56)]
    result = benchmark.summarize(rounds, ["015916"])["test"]
    assert len(result["same_timestamp_price_conflicts"]) == 1
