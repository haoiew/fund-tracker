# -*- coding: utf-8 -*-
import pytest


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
