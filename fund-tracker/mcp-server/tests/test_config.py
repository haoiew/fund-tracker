import pytest
from fund_tracker_mcp.config import Settings


@pytest.mark.parametrize("url", ["http://127.0.0.1:8001/api/v1", "http://localhost:8001/api/v1/", "http://[::1]:8001/api/v1"])
def test_accepts_only_explicit_loopback_api_urls(url):
    assert Settings(api_url=url).api_url == url.rstrip("/")


@pytest.mark.parametrize("url", ["http://example.com/api/v1", "http://0.0.0.0/api/v1", "http://192.168.1.2/api/v1",
                               "http://localhost@evil.com/api/v1", "http://user:secret@localhost/api/v1",
                               "file:///api/v1", "http://localhost/api/v1?q=secret", "http://localhost/api/v1#fragment",
                               "http://localhost/api", "http://localhost:bad/api/v1"])
def test_rejects_remote_credential_and_ambiguous_urls(url):
    with pytest.raises(ValueError):
        Settings(api_url=url)


@pytest.mark.parametrize("timeout", [0, -1, 121, float("inf"), float("nan")])
def test_timeout_is_bounded(timeout):
    with pytest.raises(ValueError):
        Settings(timeout_seconds=timeout)


def test_explicit_arguments_override_even_invalid_environment(monkeypatch):
    monkeypatch.setenv("FUND_TRACKER_API_URL", "http://evil.com/api/v1")
    monkeypatch.setenv("FUND_TRACKER_MCP_TIMEOUT", "not-a-timeout")
    assert Settings.from_env(api_url="http://localhost:8001/api/v1", timeout_seconds=20).timeout_seconds == 20
