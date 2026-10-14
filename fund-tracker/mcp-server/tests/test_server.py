import httpx
import pytest
from mcp import Client
from fund_tracker_mcp.client import BackendClient
from fund_tracker_mcp.config import Settings
from fund_tracker_mcp.server import create_server


@pytest.mark.asyncio
async def test_protocol_discovery_has_exactly_six_read_only_tools_and_typed_schemas():
    backend = BackendClient(Settings(), transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"code": 200, "data": {}})))
    async with Client(create_server(Settings(), backend=backend)) as client:
        tools = (await client.list_tools()).tools
    assert {tool.name for tool in tools} == {"get_quotes", "get_history", "compare_funds", "get_portfolio", "get_data_sources", "get_provider_catalog"}
    for tool in tools:
        assert tool.annotations.read_only_hint
        assert tool.annotations.destructive_hint is False
        assert tool.output_schema is not None
    schema = next(tool.input_schema for tool in tools if tool.name == "get_quotes")
    assert schema["properties"]["codes"]["maxItems"] == 50
    assert schema["properties"]["codes"]["items"]["pattern"] == "^[0-9]{6}$"


@pytest.mark.asyncio
async def test_tool_protocol_returns_backend_quality_and_unmodified_dates():
    seen = []
    def handle(request):
        seen.append(request)
        return httpx.Response(200, json={"code": 200, "data": [{
            "code": "015916", "estimate_nav": None, "official_update_time": "2026-10-13",
            "data_kind": "unavailable", "quality": {"nav_date": "2026-10-13", "availability": "unavailable"},
        }]})
    backend = BackendClient(Settings(), transport=httpx.MockTransport(handle))
    async with Client(create_server(Settings(), backend=backend)) as client:
        result = await client.call_tool("get_quotes", {"codes": ["015916", "015916"], "view": "nav"})
    assert not result.is_error
    assert result.structured_content["quotes"][0]["estimate_nav"] is None
    assert result.structured_content["quotes"][0]["quality"]["nav_date"] == "2026-10-13"
    assert seen[0].content == b'["015916"]'
    assert backend._client is None


@pytest.mark.asyncio
@pytest.mark.parametrize("arguments", [{"codes": []}, {"codes": ["015916"] * 51}, {"codes": ["../summary"]},
                                       {"codes": ["015916"], "view": "unknown"}])
async def test_invalid_arguments_never_reach_the_backend(arguments):
    calls = []
    def handle(request):
        calls.append(request)
        return httpx.Response(200, json={"code": 200, "data": []})
    backend = BackendClient(Settings(), transport=httpx.MockTransport(handle))
    async with Client(create_server(Settings(), backend=backend)) as client:
        result = await client.call_tool("get_quotes", arguments)
    assert result.is_error
    assert calls == []


@pytest.mark.asyncio
async def test_backend_failure_is_a_protocol_error_not_an_empty_success():
    backend = BackendClient(Settings(), transport=httpx.MockTransport(lambda r: httpx.Response(503, text="PRIVATE_API_SECRET")))
    async with Client(create_server(Settings(), backend=backend)) as client:
        result = await client.call_tool("get_provider_catalog", {})
    assert result.is_error
    assert "backend_http_error" in result.content[0].text
    assert "PRIVATE_API_SECRET" not in result.content[0].text
