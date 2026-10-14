from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.schemas.fund import FundRealtimeData
from app.services.portfolio_service import PortfolioService


@pytest.mark.asyncio
async def test_missing_quote_never_falls_back_to_purchase_cost(monkeypatch):
    service = PortfolioService()
    position = SimpleNamespace(fund_code="015916", hold_shares=Decimal("100"),
                               cost_amount=Decimal("150"), fund=SimpleNamespace(name="基金"))
    monkeypatch.setattr(service, "get_all_portfolios", lambda db: [position])
    quote = FundRealtimeData(code="015916", name="基金", data_kind="unavailable")
    result = await service.calculate_portfolio_profit(None, {"015916": quote})
    assert result.summary.total_cost == Decimal("150")
    assert result.summary.total_value is None
    assert result.summary.total_profit is None
    assert result.summary.unpriced_codes == ["015916"]
    assert result.details[0].current_value is None
    assert result.details[0].profit_amount is None


@pytest.mark.asyncio
async def test_zero_shares_are_known_zero_even_without_a_quote(monkeypatch):
    service = PortfolioService()
    position = SimpleNamespace(fund_code="015916", hold_shares=Decimal("0"),
                               cost_amount=Decimal("0"), fund=SimpleNamespace(name="基金"))
    monkeypatch.setattr(service, "get_all_portfolios", lambda db: [position])
    result = await service.calculate_portfolio_profit(None, {})
    assert result.summary.total_value == 0
    assert result.summary.unpriced_codes == []
