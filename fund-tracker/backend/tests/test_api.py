# -*- coding: utf-8 -*-
"""
API接口测试
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestHealthCheck:
    """健康检查测试"""

    def test_health_endpoint(self):
        """测试健康检查端点"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_root_endpoint(self):
        """测试根路径端点"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "docs" in data


class TestFundAPI:
    """基金API测试"""

    def test_get_default_fund_list(self):
        """测试获取默认基金列表"""
        response = client.get("/api/v1/funds/default-list")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert isinstance(data["data"], list)
        assert len(data["data"]) > 0

    def test_get_fund_realtime(self):
        """测试获取基金实时数据"""
        response = client.get("/api/v1/funds/realtime/000001")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "data" in data

    def test_search_funds(self):
        """测试搜索基金"""
        response = client.post(
            "/api/v1/funds/search",
            json={"keyword": "沪深300", "limit": 5}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert isinstance(data["data"], list)

    def test_get_fund_history(self):
        """测试获取基金历史数据"""
        response = client.get("/api/v1/funds/000001/history?range=1M")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "data" in data

    def test_screen_funds_up(self):
        """测试筛选上涨基金"""
        response = client.get(
            "/api/v1/funds/screen/up?codes=000001&codes=000002&min_days=2&min_pct=0.03"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert isinstance(data["data"], list)


class TestErrorHandling:
    """错误处理测试"""

    def test_invalid_fund_code(self):
        """测试无效基金代码"""
        response = client.get("/api/v1/funds/realtime/invalid")
        # 应该返回200，但数据中状态为错误
        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    def test_validation_error(self):
        """测试参数验证错误"""
        response = client.post(
            "/api/v1/funds/search",
            json={}  # 缺少必需参数
        )
        assert response.status_code == 422
