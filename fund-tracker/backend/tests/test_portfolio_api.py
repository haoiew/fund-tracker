# -*- coding: utf-8 -*-
import pytest


def test_fund_match_preserves_share_class():
    from app.api.v1.portfolio import _score_fund_match

    matched_score, matched_reason = _score_fund_match("招商中证白酒指数C", "招商中证白酒指数C")
    mismatch_score, mismatch_reason = _score_fund_match("招商中证白酒指数C", "招商中证白酒指数A")

    assert matched_score == 100
    assert "share_class_match" in matched_reason
    assert mismatch_score <= 82
    assert "share_class_mismatch" in mismatch_reason


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
