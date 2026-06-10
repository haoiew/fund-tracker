# -*- coding: utf-8 -*-
import asyncio
from decimal import Decimal


def test_fund_match_preserves_share_class():
    from app.api.v1.portfolio import _score_fund_match

    matched_score, matched_reason = _score_fund_match("招商中证白酒指数C", "招商中证白酒指数C")
    mismatch_score, mismatch_reason = _score_fund_match("招商中证白酒指数C", "招商中证白酒指数A")

    assert matched_score == 100
    assert "share_class_match" in matched_reason
    assert mismatch_score <= 82
    assert "share_class_mismatch" in mismatch_reason


def test_truncated_fund_name_generates_multiple_search_keywords():
    from app.api.v1.portfolio import _build_fund_search_keywords

    keywords = _build_fund_search_keywords("景顺长城纳斯达克科技ETF联接(...")

    assert keywords[0] == "景顺长城纳斯达克科技ETF联接"
    assert "景顺长城纳斯达克" in keywords
    assert len(set(keywords)) == len(keywords)


def test_ai_url_join_accepts_base_url_with_or_without_chat_path():
    from app.api.v1.portfolio import _join_ai_url

    assert _join_ai_url("https://api.example.com/v1", "/chat/completions") == "https://api.example.com/v1/chat/completions"
    assert _join_ai_url("https://api.example.com/v1/chat/completions", "/chat/completions") == "https://api.example.com/v1/chat/completions"


def test_ai_connection_test_omits_temperature(client, monkeypatch):
    from app.api.v1 import portfolio as portfolio_api

    captured = {}

    async def fake_call_ai_chat_completion(**kwargs):
        captured.update(kwargs)
        return {"choices": [{"message": {"content": "OK"}}]}, 123, 200

    monkeypatch.setattr(portfolio_api, "_call_ai_chat_completion", fake_call_ai_chat_completion)

    resp = client.post("/api/v1/portfolio/ai-connection-test", json={
        "model": "test-model",
        "base_url": "https://api.example.com/v1",
        "api_key": "test-key",
    })

    assert resp.status_code == 200
    assert "temperature" not in captured
    assert captured["max_tokens"] == 8
    assert captured["messages"][0]["content"] == "只回复 OK，用于接口连通性检测。"


def test_ai_connection_test_can_validate_vision_input(client, monkeypatch):
    from app.api.v1 import portfolio as portfolio_api

    captured_calls = []

    async def fake_call_ai_chat_completion(**kwargs):
        captured_calls.append(kwargs)
        return {"choices": [{"message": {"content": "OK"}}]}, 123, 200

    monkeypatch.setattr(portfolio_api, "_call_ai_chat_completion", fake_call_ai_chat_completion)

    resp = client.post("/api/v1/portfolio/ai-connection-test", json={
        "model": "test-model",
        "base_url": "https://api.example.com/v1",
        "api_key": "test-key",
        "include_vision": True,
    })

    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["vision_latency_ms"] == 123
    assert len(captured_calls) == 2
    vision_content = captured_calls[1]["messages"][0]["content"]
    assert isinstance(vision_content, list)
    assert vision_content[1]["type"] == "image_url"


def test_ai_recognize_empty_content_reports_model(client, monkeypatch):
    from app.api.v1 import portfolio as portfolio_api

    async def fake_call_ai_chat_completion(**kwargs):
        return {"choices": [{"message": {"content": ""}}]}, 123, 200

    monkeypatch.setattr(portfolio_api, "_call_ai_chat_completion", fake_call_ai_chat_completion)

    resp = client.post("/api/v1/portfolio/ai-recognize", json={
        "image_base64": "data:image/png;base64,AA==",
        "model": "GPT-5.5",
        "base_url": "https://api.example.com/v1",
        "api_key": "test-key",
    })

    assert resp.status_code == 502
    assert "AI返回内容为空: model=gpt-5.5" in resp.json()["detail"]


def test_ai_chat_completion_uses_max_completion_tokens(monkeypatch):
    from app.api.v1 import portfolio as portfolio_api

    captured = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": "OK"}}]}

    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, headers, json):
            captured["url"] = url
            captured["headers"] = headers
            captured["payload"] = json
            return FakeResponse()

    monkeypatch.setattr(portfolio_api.httpx, "AsyncClient", FakeClient)

    asyncio.run(
        portfolio_api._call_ai_chat_completion(
            base_url="https://api.example.com/v1",
            api_key="test-key",
            model="GPT-5.5",
            messages=[{"role": "user", "content": "OK"}],
            timeout=portfolio_api._AI_TEST_TIMEOUT,
            max_tokens=8,
        )
    )

    assert captured["url"] == "https://api.example.com/v1/chat/completions"
    assert captured["payload"]["model"] == "gpt-5.5"
    assert captured["payload"]["max_completion_tokens"] == 8
    assert "max_tokens" not in captured["payload"]


def test_portfolio_crud_and_summary(client):
    create_payload = {
        "fund_code": "000001",
        "hold_shares": "10",
        "cost_amount": "100",
        "cost_nav": "1.0000",
        "remark": "test",
    }
    resp = client.post("/api/v1/portfolio", json=create_payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    portfolio_id = body["data"]["id"]

    resp = client.get("/api/v1/portfolio")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert isinstance(body["data"], list)
    assert len(body["data"]) == 1

    resp = client.get("/api/v1/portfolio/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert set(body["data"].keys()) == {"items", "stats"}
    assert isinstance(body["data"]["items"], list)

    stats = body["data"]["stats"]
    for key in ["total_cost", "total_value", "total_profit_loss", "total_profit_loss_pct", "item_count"]:
        assert key in stats

    resp = client.put(f"/api/v1/portfolio/{portfolio_id}", json={"remark": "updated"})
    assert resp.status_code == 200
    assert resp.json()["data"]["remark"] == "updated"

    resp = client.get(f"/api/v1/portfolio/{portfolio_id}")
    assert resp.status_code == 200
    assert resp.json()["data"]["remark"] == "updated"

    resp = client.delete(f"/api/v1/portfolio/{portfolio_id}")
    assert resp.status_code == 200
    assert resp.json()["message"] == "删除成功"

    resp = client.get("/api/v1/portfolio")
    assert resp.status_code == 200
    assert resp.json()["data"] == []


def test_get_missing_portfolio_returns_404(client):
    resp = client.get("/api/v1/portfolio/999999")
    assert resp.status_code == 404


def test_portfolio_transactions_recalculate_position(client):
    resp = client.post("/api/v1/portfolio", json={
        "fund_code": "000002",
        "fund_name": "测试基金",
        "hold_shares": "10",
        "cost_amount": "100",
        "cost_nav": "10.0000",
        "buy_date": "2026-06-01",
    })
    assert resp.status_code == 200
    portfolio_id = resp.json()["data"]["id"]
    assert resp.json()["data"]["transaction_count"] == 1

    resp = client.get(f"/api/v1/portfolio/{portfolio_id}/transactions")
    assert resp.status_code == 200
    transactions = resp.json()["data"]
    assert len(transactions) == 1
    assert transactions[0]["transaction_type"] == "snapshot"

    resp = client.post("/api/v1/portfolio/transactions", json={
        "portfolio_id": portfolio_id,
        "transaction_type": "buy",
        "trade_date": "2026-06-05",
        "shares": "5",
        "amount": "60",
        "nav": "12.0000",
    })
    assert resp.status_code == 200
    assert resp.json()["data"]["transaction_type"] == "buy"

    resp = client.get(f"/api/v1/portfolio/{portfolio_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["hold_shares"] == "15.0000"
    assert data["cost_amount"] == "160.00"
    assert data["cost_nav"] == "10.6667"
    assert data["transaction_count"] == 2


def test_import_preview_blocks_unsafe_items(client):
    client.post("/api/v1/portfolio", json={
        "fund_code": "000003",
        "hold_shares": "10",
        "cost_amount": "100",
        "cost_nav": "10.0000",
    })

    resp = client.post("/api/v1/portfolio/import/preview", json={
        "strict": True,
        "holdings": [
            {
                "fund_code": "000003",
                "fund_name": "已存在基金",
                "market_value": "100",
                "holding_return": "10",
                "match_status": "matched",
                "confidence": 100,
            },
            {
                "fund_code": "000004",
                "fund_name": "模糊基金",
                "market_value": "200",
                "holding_return": "20",
                "match_status": "ambiguous",
                "confidence": 85,
            },
            {
                "fund_code": "000005",
                "fund_name": "可导入基金",
                "market_value": "300",
                "holding_return": "30",
                "match_status": "matched",
                "confidence": 95,
            },
        ]
    })
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["ready_count"] == 1
    assert data["skipped_count"] == 2
    assert data["invalid_count"] == 0
    assert data["items"][0]["status"] == "skipped"
    assert data["items"][1]["status"] == "skipped"
    assert data["items"][2]["status"] == "ready"
    assert data["items"][2]["current_nav"] == "1.2345"
    assert data["items"][2]["estimated_shares"] == "243.0134"
    assert data["items"][2]["estimated_cost"] == "270.00"
    assert data["items"][2]["estimated_cost_nav"] == "1.1111"


def test_import_confirm_creates_ready_items_and_skips_unsafe_items(client):
    resp = client.post("/api/v1/portfolio/import/confirm", json={
        "strict": True,
        "trade_date": "2026-06-06",
        "holdings": [
            {
                "row_index": 1,
                "fund_code": "000006",
                "fund_name": "可导入基金A",
                "market_value": "300",
                "daily_return": "-1.23",
                "holding_return": "30",
                "holding_return_rate": "11.11",
                "match_status": "matched",
                "confidence": 100,
            },
            {
                "row_index": 2,
                "fund_code": "000007",
                "fund_name": "截断基金",
                "market_value": "200",
                "holding_return": "20",
                "match_status": "ambiguous",
                "confidence": 80,
            },
        ]
    })
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["success_count"] == 1
    assert data["skipped_count"] == 1
    assert data["failed_count"] == 0
    assert data["items"][0]["status"] == "success"
    assert data["items"][1]["status"] == "skipped"

    resp = client.get("/api/v1/portfolio")
    assert resp.status_code == 200
    portfolios = resp.json()["data"]
    portfolio = next((item for item in portfolios if item["fund_code"] == "000006"), None)
    assert portfolio is not None
    assert portfolio["fund_code"] == "000006"
    assert portfolio["hold_shares"] == "243.0134"
    assert portfolio["cost_amount"] == "270.00"
    assert portfolio["cost_nav"] == "1.1111"
    assert portfolio["buy_date"] == "2026-06-06"

    resp = client.get(f"/api/v1/portfolio/{portfolio['id']}/transactions")
    assert resp.status_code == 200
    transactions = resp.json()["data"]
    assert len(transactions) == 1
    assert transactions[0]["transaction_type"] == "snapshot"
    assert transactions[0]["source"] == "import"


def test_import_confirm_overwrite_updates_existing_position(client):
    client.post("/api/v1/portfolio", json={
        "fund_code": "000008",
        "fund_name": "覆盖基金",
        "hold_shares": "100",
        "cost_amount": "100",
        "cost_nav": "1.0000",
    })

    resp = client.post("/api/v1/portfolio/import/confirm", json={
        "mode": "overwrite",
        "strict": True,
        "trade_date": "2026-06-07",
        "holdings": [{
            "fund_code": "000008",
            "fund_name": "覆盖基金",
            "market_value": "300",
            "holding_return": "30",
            "match_status": "matched",
            "confidence": 100,
        }]
    })

    assert resp.status_code == 200
    assert resp.json()["data"]["success_count"] == 1

    resp = client.get("/api/v1/portfolio")
    portfolio = next(item for item in resp.json()["data"] if item["fund_code"] == "000008")
    assert portfolio["hold_shares"] == "243.0134"
    assert portfolio["cost_amount"] == "270.00"
    assert portfolio["cost_nav"] == "1.1111"


def test_import_confirm_rebalance_records_inferred_adjustment(client):
    client.post("/api/v1/portfolio", json={
        "fund_code": "000009",
        "fund_name": "调仓基金",
        "hold_shares": "100",
        "cost_amount": "100",
        "cost_nav": "1.0000",
    })

    resp = client.post("/api/v1/portfolio/import/confirm", json={
        "mode": "rebalance",
        "strict": True,
        "trade_date": "2026-06-08",
        "holdings": [{
            "fund_code": "000009",
            "fund_name": "调仓基金",
            "market_value": "300",
            "holding_return": "30",
            "match_status": "matched",
            "confidence": 100,
        }]
    })

    assert resp.status_code == 200
    assert resp.json()["data"]["success_count"] >= 1

    resp = client.get("/api/v1/portfolio/rebalance-records")
    assert resp.status_code == 200
    records = resp.json()["data"]
    record = next(item for item in records if item["fund_code"] == "000009")
    assert record["action_type"] == "increase"
    assert record["inferred_amount"] == "170.00"
    assert record["trade_date"] == "2026-06-08"


def test_ai_recognize_transactions_parses_and_matches(client, monkeypatch):
    from app.api.v1 import portfolio as portfolio_api
    from app.services import fund_service as fund_service_module

    service = fund_service_module.get_fund_service()
    monkeypatch.setattr(service, "search_funds", lambda keyword, limit=12: [{
        "code": "000010",
        "name": "招商中证白酒指数C",
    }])

    async def fake_call_ai_chat_completion(**kwargs):
        return {
            "choices": [{
                "message": {
                    "content": '{"expected_count":1,"transactions":[{"row_index":1,"raw_fund_name":"转入-招商中证白酒指数C","fund_name":"招商中证白酒指数C","trade_date":"06-02","trade_time":"14:57:07","amount":100,"order_status":"订单完成"}]}'
                }
            }]
        }, 123, 200

    monkeypatch.setattr(portfolio_api, "_call_ai_chat_completion", fake_call_ai_chat_completion)

    resp = client.post("/api/v1/portfolio/ai-recognize-transactions", json={
        "image_base64": "data:image/png;base64,AA==",
        "model": "test-model",
        "base_url": "https://api.example.com/v1",
        "api_key": "test-key",
        "default_year": 2026,
    })

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["transactions"][0]["fund_code"] == "000010"
    assert data["transactions"][0]["transaction_type"] == "buy"
    assert data["transactions"][0]["trade_date"] == "2026-06-02"
    assert data["transactions"][0]["order_status"] == "订单完成"


def test_transaction_import_confirm_creates_transaction(client):
    resp = client.post("/api/v1/portfolio/transactions/import/confirm", json={
        "strict": True,
        "transactions": [{
            "fund_code": "000011",
            "fund_name": "交易导入基金",
            "transaction_type": "buy",
            "trade_date": "2026-06-02",
            "trade_time": "14:57:07",
            "amount": "123.45",
            "order_status": "订单完成",
            "match_status": "matched",
            "confidence": 100,
        }]
    })

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["success_count"] == 1
    portfolio_id = data["items"][0]["portfolio_id"]

    resp = client.get(f"/api/v1/portfolio/{portfolio_id}/transactions")
    assert resp.status_code == 200
    transactions = resp.json()["data"]
    assert len(transactions) == 1
    assert transactions[0]["transaction_type"] == "buy"
    assert transactions[0]["source"] == "ai_txn"


def test_realtime_alternatives_exposes_fallback_estimate(client, monkeypatch):
    from app.schemas.fund import FundRealtimeData
    from app.services import fund_service as fund_service_module

    service = fund_service_module.get_fund_service()

    async def fake_realtime_data(code: str) -> FundRealtimeData:
        return FundRealtimeData(
            code=code,
            name="天弘标普500发起(QDII-FOF)C",
            estimate_nav=Decimal("2.2046"),
            estimate_change=Decimal("0.35"),
            update_time="2026-06-04",
            status="最新净值",
            data_source="eastmoney_lsjz",
            data_kind="latest_nav",
            data_kind_label="最新净值",
            is_realtime=False,
        )

    async def fake_comparison(code: str, name: str | None = None):
        return {
            "code": code,
            "name": name or "天弘标普500发起(QDII-FOF)C",
            "sources": [{
                "source": "tencent",
                "display_name": "腾讯基金行情",
                "estimate_change_pct": 0.3459,
                "update_time": "2026-06-04",
                "is_realtime": False,
                "is_fresh": True,
            }],
            "best_source": "tencent",
            "best_source_display_name": "腾讯基金行情",
            "total_sources": 1,
        }

    monkeypatch.setattr(service, "get_realtime_data", fake_realtime_data)
    monkeypatch.setattr(service, "get_data_source_comparison", fake_comparison)
    monkeypatch.setattr(service, "_estimate_from_holdings", lambda code: {
        "feasible": False,
        "reason": "no_parseable_f10_holdings_with_weights",
    })

    resp = client.get("/api/v1/funds/007722/realtime-alternatives")

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["holdings_based_estimate"]["feasible"] is False
    assert data["fallback_estimate"]["feasible"] is True
    assert data["fallback_estimate"]["source"] == "tencent"
    assert data["fallback_estimate"]["change_pct"] == 0.3459


def test_f10_qdii_hk_stock_holdings_are_parseable(monkeypatch):
    from app.services import fund_service as fund_service_module

    service = fund_service_module.get_fund_service()
    sample = """
    截止至：<font>2026-03-31</font>
    <tr><th>序号</th><th>股票代码</th><th>股票名称</th><th>占净值比例</th></tr>
    <tr><td>1</td><td><a href='http://quote.eastmoney.com/unify/r/116.00700'>00700</a></td><td><a href='http://quote.eastmoney.com/unify/r/116.00700'>腾讯控股</a></td><td>4.12%</td></tr>
    """

    monkeypatch.setattr(service, "_fetch_f10_holding_section", lambda code, section_type: sample if section_type == "jjcc" else "")

    payload = service._fetch_f10_top_holdings("160125")

    assert payload["source_type"] == "jjcc"
    assert payload["position_date"] == "2026-03-31"
    assert payload["holdings"][0]["symbol"] == "hk00700"
    assert payload["holdings"][0]["weight"] == 4.12


def test_reference_symbol_estimate_for_silver_and_sp500(monkeypatch):
    from app.services import fund_service as fund_service_module

    service = fund_service_module.get_fund_service()
    monkeypatch.setattr(service, "_fetch_tencent_quote_changes", lambda symbols: {
        "sz161226": -6.73,
        "usSPY": -2.58,
    })

    silver = service._estimate_from_reference_symbols("161226", "国投瑞银白银期货(LOF)A")
    sp500 = service._estimate_from_reference_symbols("007722", "天弘标普500发起(QDII-FOF)C")

    assert silver["feasible"] is True
    assert silver["weighted_stock_change_pct"] == -6.73
    assert silver["references"][0]["symbol"] == "sz161226"
    assert sp500["feasible"] is True
    assert sp500["weighted_stock_change_pct"] == -2.58
    assert sp500["references"][0]["symbol"] == "usSPY"


def test_zqcc_holdings_return_non_quoteable_details(monkeypatch):
    from app.services import fund_service as fund_service_module

    service = fund_service_module.get_fund_service()
    sample = """
    <tr><th>序号</th><th>债券代码</th><th>债券名称</th><th>占净值比例</th><th>持仓市值（万元）</th></tr>
    <tr><td>1</td><td>102298</td><td>国债2508</td><td>3.63%</td><td>14185.84</td></tr>
    """
    monkeypatch.setattr(service, "_fetch_f10_holding_section", lambda code, section_type: "" if section_type == "jjcc" else sample)

    payload = service._fetch_f10_top_holdings("007722")
    estimate = service._estimate_from_holdings("007722")

    assert payload["source_type"] == "zqcc"
    assert payload["holdings"][0]["holding_type"] == "bond_or_fund"
    assert estimate["feasible"] is False
    assert estimate["reason"] == "no_quoteable_symbols_in_f10_holdings"
    assert estimate["top_holdings"][0]["name"] == "国债2508"
