"""Isolated provider-contract tests: no network, user data or SDK imports."""
import json
from unittest.mock import Mock

import pytest

from app.services.fund_service import FundService


@pytest.fixture
def service():
    service = object.__new__(FundService)
    service.session = Mock()
    return service


def test_index_uses_close_not_open_or_accumulated_values(service):
    response = service.session.get.return_value
    response.json.return_value = {"data": {"klines": [
        "2026-10-13,900,1000", "2026-10-14,1001,1100", "invalid,9,12", "2026-10-12,9,-1",
    ]}}
    frame = service._get_index_daily("sh000300")
    assert frame["close"].tolist() == [1000, 1100]
    assert service.session.get.call_args.kwargs["params"]["secid"] == "1.000300"
    with pytest.raises(ValueError):
        service._get_index_daily("https://example.com")


def test_rank_array_is_decoded_without_evaluating_javascript(service):
    response = service.session.get.return_value
    # Synthetic contract fixture, confined to tests.
    rows = ["000001,测试[基金],CSJJ,2026-10-13,1.1,2.2,1.5,2,3,4,5",
            "000002,测试基金,CSJJ,2026-10-13,1,2,-1,-2,-3,-4,-5",
            "bad,row"]
    response.text = "var rankData = {datas:" + json.dumps(rows) + ",allRecords:2}; throw new Error('not executed');"
    assert service._get_market_rank_candidates("up", 1, "consecutive") == ["000001"]
    assert service._get_market_rank_candidates("down", 30, "period") == ["000002"]
    params = service.session.get.call_args.kwargs["params"]
    assert params["pn"] == "30000"
    response.text = "var rankData = {error:'unavailable'}"
    with pytest.raises(ValueError):
        service._get_market_rank_data()
