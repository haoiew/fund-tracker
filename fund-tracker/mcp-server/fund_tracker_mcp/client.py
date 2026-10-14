"""Fixed read-only API surface; no arbitrary HTTP tool, DB access, or financial calculations."""
from typing import Any

import httpx

from .config import Settings


class BackendError(RuntimeError):
    """Safe protocol error; no raw request/response body or sensitive URL is reflected."""


class BackendClient:
    def __init__(self, settings: Settings, *, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self.transport = transport
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            base_url=self.settings.api_url + "/", transport=self.transport,
            timeout=httpx.Timeout(self.settings.timeout_seconds, connect=5),
            trust_env=False, follow_redirects=False,
        )
        return self

    async def __aexit__(self, *args):
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _read(self, method: str, path: str, **kwargs) -> Any:
        if self._client is None:
            raise BackendError("backend_not_started: MCP client lifecycle is not active")
        try:
            response = await self._client.request(method, path, **kwargs)
        except httpx.TimeoutException:
            raise BackendError("backend_timeout: local backend timed out; no data was fabricated") from None
        except httpx.RequestError:
            raise BackendError("backend_unavailable: start the local Fund Tracker backend first") from None
        if response.status_code != 200:
            raise BackendError(f"backend_http_error: local backend returned HTTP {response.status_code}")
        try:
            payload = response.json()
        except ValueError:
            raise BackendError("invalid_backend_response: expected a JSON API envelope") from None
        if not isinstance(payload, dict) or payload.get("code") != 200 or "data" not in payload:
            raise BackendError("invalid_backend_response: expected code=200 and a data field")
        if payload["data"] is None:
            raise BackendError("empty_backend_response: the backend supplied no data")
        return payload["data"]

    async def get_quotes(self, codes: list[str], view: str) -> dict[str, Any]:
        quotes = await self._read("POST", "funds/realtime/batch", json=codes, params={"view": view})
        if not isinstance(quotes, list):
            raise BackendError("invalid_backend_response: expected a quote list")
        return {"quotes": quotes}

    async def get_history(self, code: str, range: str) -> dict[str, Any]:
        data = await self._read("GET", f"funds/{code}/history", params={"range": range})
        if not isinstance(data, dict):
            raise BackendError("invalid_backend_response: expected history data")
        return {"code": code, "range": range, **data}

    async def compare_funds(self, codes: list[str], range: str, include_benchmark: bool) -> dict[str, Any]:
        data = await self._read("POST", "funds/compare", json={
            "codes": codes, "range": range, "include_benchmark": include_benchmark,
        })
        if not isinstance(data, dict):
            raise BackendError("invalid_backend_response: expected comparison data")
        return data

    async def get_portfolio(self, include_quotes: bool) -> dict[str, Any]:
        data = await self._read("GET", "portfolio/summary", params={"include_quotes": include_quotes})
        if not isinstance(data, dict):
            raise BackendError("invalid_backend_response: expected a portfolio summary")
        return data

    async def get_data_sources(self, code: str) -> dict[str, Any]:
        data = await self._read("GET", f"funds/{code}/data-sources")
        if not isinstance(data, dict):
            raise BackendError("invalid_backend_response: expected source comparison data")
        return data

    async def get_provider_catalog(self) -> dict[str, Any]:
        data = await self._read("GET", "funds/providers")
        if not isinstance(data, dict):
            raise BackendError("invalid_backend_response: expected the provider catalog")
        return data
