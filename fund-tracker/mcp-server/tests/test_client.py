import json
import httpx
import pytest
from fund_tracker_mcp.client import BackendClient, BackendError
from fund_tracker_mcp.config import Settings


@pytest.mark.asyncio
async def test_reads_use_only_six_fixed_api_routes_and_preserve_nulls_and_quality():
    requests = []
    # Synthetic API fixtures are test-only, never fallbacks in the adapter.
    def handle(request):
        requests.append(request)
        if request.url.path.endswith("realtime/batch"):
            data = [{"code": "015916", "estimate_nav": None, "quality": {"availability": "unavailable"}}]
        else:
            data = {"source": "test", "return_basis": "provider_daily_return"}
        return httpx.Response(200, json={"code": 200, "data": data})
    async with BackendClient(Settings(), transport=httpx.MockTransport(handle)) as backend:
        result = await backend.get_quotes(["015916"], "provider")
        assert result["quotes"][0]["estimate_nav"] is None
        assert result["quotes"][0]["quality"]["availability"] == "unavailable"
        await backend.get_history("015916", "1M")
        comparison = await backend.compare_funds(["015916"], "1M", False)
        assert comparison["return_basis"] == "provider_daily_return"
        await backend.get_portfolio(False)
        await backend.get_data_sources("015916")
        await backend.get_provider_catalog()
    assert [(r.method, r.url.path) for r in requests] == [
        ("POST", "/api/v1/funds/realtime/batch"), ("GET", "/api/v1/funds/015916/history"),
        ("POST", "/api/v1/funds/compare"), ("GET", "/api/v1/portfolio/summary"),
        ("GET", "/api/v1/funds/015916/data-sources"), ("GET", "/api/v1/funds/providers"),
    ]
    assert json.loads(requests[0].content) == ["015916"]
    assert requests[0].url.params["view"] == "provider"
    assert requests[3].url.params["include_quotes"] == "false"
    assert all("authorization" not in r.headers for r in requests)


@pytest.mark.asyncio
@pytest.mark.parametrize("response", [httpx.Response(200, text="not JSON"),
                                     httpx.Response(200, json={"code": 500, "data": {}}),
                                     httpx.Response(200, json={"code": 200}),
                                     httpx.Response(200, json={"code": 200, "data": None}),
                                     httpx.Response(500, text="PRIVATE_API_SECRET"),
                                     httpx.Response(302, headers={"location": "https://evil.example/api/v1"})])
async def test_invalid_error_or_redirect_responses_fail_without_reflecting_secrets(response):
    calls = []
    def handle(request):
        calls.append(request)
        return response
    async with BackendClient(Settings(), transport=httpx.MockTransport(handle)) as backend:
        with pytest.raises(BackendError) as error:
            await backend.get_provider_catalog()
    assert "PRIVATE_API_SECRET" not in str(error.value)
    assert len(calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("exception,code", [(httpx.ConnectError, "backend_unavailable"), (httpx.ReadTimeout, "backend_timeout")])
async def test_connection_and_timeout_errors_are_explicit(exception, code):
    def handle(request):
        raise exception("PRIVATE_API_SECRET", request=request)
    async with BackendClient(Settings(), transport=httpx.MockTransport(handle)) as backend:
        with pytest.raises(BackendError, match=code) as error:
            await backend.get_provider_catalog()
    assert "PRIVATE_API_SECRET" not in str(error.value)


@pytest.mark.asyncio
async def test_proxy_environment_is_never_used(monkeypatch):
    monkeypatch.setenv("HTTP_PROXY", "http://evil.example:9999")
    monkeypatch.setenv("HTTPS_PROXY", "http://evil.example:9999")
    async with BackendClient(Settings()) as backend:
        assert not backend._client._trust_env
        assert not backend._client.follow_redirects
