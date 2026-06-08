# -*- coding: utf-8 -*-
import pytest


def test_health_endpoint(client):
    resp = client.get("/api/v1/system/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200


def test_root_endpoint(client):
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert "name" in data
    assert "version" in data
    assert "docs" in data


def test_api_v1_prefix(client):
    """测试 API 路由前缀 /api/v1 是否正确挂载"""
    resp = client.get("/api/v1/funds/default-list")
    assert resp.status_code == 200


def test_response_wrapper_format(client):
    """测试 API 响应包装格式: { code, data, message }"""
    resp = client.get("/api/v1/funds/default-list")
    assert resp.status_code == 200
    body = resp.json()
    assert "code" in body, "响应应包含 code 字段"
    assert "data" in body, "响应应包含 data 字段"
    assert body["code"] == 200, "成功响应 code 应为 200"


def test_cors_headers(client):
    """测试 CORS 头是否正确设置"""
    resp = client.options("/api/v1/funds/default-list", headers={
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "GET"
    })
    assert resp.status_code == 200


def test_get_default_fund_list(client):
    resp = client.get("/api/v1/funds/default-list")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert isinstance(body["data"], list)
    assert len(body["data"]) > 0


def test_get_fund_data_sources(client, monkeypatch):
    import app.api.v1.funds as funds_api

    class FakeFundService:
        async def get_data_source_comparison(self, code: str, name: str | None = None):
            return {
                "code": code,
                "name": name or f"基金{code}",
                "sources": [
                    {
                        "source": "tiantian",
                        "priority": 1,
                        "estimate_nav": 1.2345,
                        "estimate_change_pct": 0.5,
                        "last_nav": None,
                        "last_change_pct": None,
                        "update_time": "2026-06-08 14:30",
                        "is_fresh": True,
                        "error": None,
                    }
                ],
                "best_source": "tiantian",
                "total_sources": 1,
            }

    monkeypatch.setattr(funds_api, "get_fund_service", lambda: FakeFundService())

    resp = client.get("/api/v1/funds/012414/data-sources", params={"name": "招商中证白酒指数(LOF)C"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["code"] == "012414"
    assert body["data"]["name"] == "招商中证白酒指数(LOF)C"
    assert body["data"]["best_source"] == "tiantian"
    assert body["data"]["sources"][0]["estimate_nav"] == 1.2345


def test_data_source_metadata_classifies_realtime_and_latest_nav():
    from app.core.data_source import _classify_data_kind, get_data_source_metadata

    tiantian = get_data_source_metadata("tiantian")
    assert tiantian["display_name"] == "天天基金盘中估值接口"
    assert tiantian["short_name"] == "TTFund"
    assert _classify_data_kind("tiantian", "2026-06-08 11:30") == ("realtime_estimate", "实时估值")
    assert _classify_data_kind("eastmoney_lsjz", "2026-06-05") == ("latest_nav", "最新净值")


@pytest.mark.integration
def test_fund_endpoints_integration(client):
    resp = client.get("/api/v1/funds/realtime/000001")
    assert resp.status_code == 200

    resp = client.post("/api/v1/funds/search", json={"keyword": "沪深300", "limit": 5})
    assert resp.status_code in (200, 422)

    resp = client.get("/api/v1/funds/000001/history?range=1M")
    assert resp.status_code == 200

    resp = client.get("/api/v1/funds/screen/up?codes=000001&codes=000002&min_days=2&min_pct=0.03")
    assert resp.status_code == 200
