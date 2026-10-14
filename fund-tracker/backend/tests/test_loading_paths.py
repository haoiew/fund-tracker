"""Loading regressions: local holdings must not depend on remote quotes."""
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest


@pytest.mark.asyncio
async def test_metadata_summary_does_not_fetch_quotes_or_resolve_names(monkeypatch):
    from app.api.v1.portfolio import _build_portfolio_summary, portfolio_service
    from app.services import fund_service

    position = SimpleNamespace(
        id=1, fund_code="015916", fund=None, hold_shares=Decimal("100"),
        cost_amount=Decimal("150"), cost_nav=None, buy_date=None, remark=None,
        created_at=datetime(2026, 10, 14), updated_at=None, transactions=[],
    )
    monkeypatch.setattr(portfolio_service, "get_all_portfolios", lambda db: [position])

    def no_remote_service():
        raise AssertionError("metadata must not access the remote fund service")

    monkeypatch.setattr(fund_service, "get_fund_service", no_remote_service)
    data = await _build_portfolio_summary(None, include_quotes=False)
    assert data["items"][0].fund_code == "015916"
    assert data["items"][0].hold_shares == 100
    assert data["items"][0].current_nav is None
    assert data["stats"]["total_cost"] == 150
    assert data["stats"]["total_value"] is None
    assert data["stats"]["unpriced_codes"] == ["015916"]


def test_disclosed_holdings_are_cached_independently_of_live_quotes(monkeypatch):
    from app.services.fund_service import FundService

    service = FundService()
    service.cache.delete("f10_holdings:015916")
    calls = []
    sample = """
    截止至：<font>2026-06-30</font>
    <table><tr><td>1</td><td>600519</td><td>贵州茅台</td><td>4.12%</td></tr></table>
    """
    monkeypatch.setattr(service, "_fetch_f10_holding_section", lambda *args: calls.append(args) or sample)
    try:
        first = service._fetch_f10_top_holdings("015916")
        second = service._fetch_f10_top_holdings("015916")
        assert first == second
        assert calls == [("015916", "jjcc")]
        assert first["position_date"] == "2026-06-30"
    finally:
        service.cache.delete("f10_holdings:015916")


def test_failed_holdings_request_is_not_cached(monkeypatch):
    from app.services.fund_service import FundService

    service = FundService()
    service.cache.delete("f10_holdings:015916")
    calls = []

    def fail(*args):
        calls.append(args)
        raise TimeoutError("test timeout")

    monkeypatch.setattr(service, "_fetch_f10_holding_section", fail)
    for _ in range(2):
        with pytest.raises(TimeoutError):
            service._fetch_f10_top_holdings("015916")
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_concurrent_clients_share_one_inference(monkeypatch):
    import asyncio
    import time
    from app.services.fund_service import FundService
    from app.schemas.fund import FundRealtimeData

    service = FundService()
    service.cache.delete("quote_alternatives:015916:False")
    calls = []

    async def direct(*args):
        return FundRealtimeData(code="015916", name="基金", data_kind="latest_nav")

    def holdings(code):
        calls.append(code)
        time.sleep(0.02)
        return {"feasible": False, "reason": "test"}

    monkeypatch.setattr(service, "_get_direct_realtime_data", direct)
    monkeypatch.setattr(service, "_estimate_from_holdings", holdings)
    monkeypatch.setattr(service, "_estimate_from_reference_symbols", lambda *args: {"feasible": False})
    try:
        first, second = await asyncio.gather(*[
            service.get_realtime_alternatives("015916", include_candidates=False) for _ in range(2)
        ])
        assert first == second
        assert calls == ["015916"]
    finally:
        service.cache.delete("quote_alternatives:015916:False")


def test_f10_frequency_limit_stops_other_requests_during_cooldown(monkeypatch):
    import requests
    from app.config import settings
    from app.services.fund_service import FundService

    service = FundService()
    calls = []
    monkeypatch.setattr(service, "_holdings_retry_at", 0.0, raising=False)
    monkeypatch.setattr(settings, "HOLDINGS_REQUEST_INTERVAL", 0.0, raising=False)

    def limited(*args, **kwargs):
        calls.append(args)

        def raise_error():
            raise requests.HTTPError("HTTP 514 Frequency Capped")

        return SimpleNamespace(status_code=514, headers={}, raise_for_status=raise_error)

    monkeypatch.setattr(service.session, "get", limited)
    for code in ("015916", "015790"):
        with pytest.raises(requests.HTTPError, match="514|限流"):
            service._fetch_f10_holding_section(code, "jjcc")
    assert len(calls) == 1
