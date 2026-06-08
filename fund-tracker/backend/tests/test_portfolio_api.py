# -*- coding: utf-8 -*-
import asyncio


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
