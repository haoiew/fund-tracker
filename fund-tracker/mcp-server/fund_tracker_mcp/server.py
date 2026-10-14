"""Six explicit read-only tools. Official MCP SDK only; no standalone FastMCP dependency."""
from contextlib import asynccontextmanager
from typing import Annotated, Any, Awaitable, Literal

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field, StringConstraints

from . import __version__
from .client import BackendClient, BackendError
from .config import Settings

FundCode = Annotated[str, StringConstraints(pattern=r"^[0-9]{6}$")]
TimeRange = Literal["1W", "1M", "3M", "6M", "1Y", "ALL"]


async def _read_backend(request: Awaitable[dict[str, Any]]) -> dict[str, Any]:
    try:
        return await request
    except BackendError as exc:
        # Only our sanitized expected failures are exposed; unexpected crashes stay masked by the SDK.
        raise ToolError(str(exc)) from None


def create_server(settings: Settings, *, backend: BackendClient | None = None) -> MCPServer:
    backend = backend or BackendClient(settings)

    @asynccontextmanager
    async def lifespan(server):
        async with backend:
            yield None

    server = MCPServer(
        "fund-tracker", version=__version__, lifespan=lifespan,
        instructions=(
            "Local read-only Fund Tracker adapter. All finance logic and quote selection live in the backend. "
            "Report data_kind, quality, source_time and NAV dates. Never treat cumulative NAV as a unit price, "
            "a provider estimate as official NAV, fetched_at as quote time, or null/error as zero or cost price. "
            "Portfolio data is private. These tools do not edit holdings, lists, settings or transactions."
        ),
    )
    read_only = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True)

    @server.tool(annotations=read_only, structured_output=True)
    async def get_quotes(codes: Annotated[list[FundCode], Field(min_length=1, max_length=50)],
                         view: Literal["auto", "provider", "nav"] = "auto") -> dict[str, Any]:
        """Query backend-selected quotes. auto/provider/nav retain the backend's exact selection policy and quality."""
        return await _read_backend(backend.get_quotes(list(dict.fromkeys(codes)), view))

    @server.tool(annotations=read_only, structured_output=True)
    async def get_history(code: FundCode, range: TimeRange = "3M") -> dict[str, Any]:
        """Read dated historical NAV and its backend-provided basis; no MCP-side return calculation."""
        return await _read_backend(backend.get_history(code, range))

    @server.tool(annotations=read_only, structured_output=True)
    async def compare_funds(codes: Annotated[list[FundCode], Field(min_length=1, max_length=10)],
                            range: TimeRange = "3M", include_benchmark: bool = True) -> dict[str, Any]:
        """Compare funds with the backend's aligned returns and explicit return basis; does not edit a watchlist."""
        return await _read_backend(backend.compare_funds(list(dict.fromkeys(codes)), range, include_benchmark))

    @server.tool(annotations=read_only, structured_output=True)
    async def get_portfolio(include_quotes: bool = False) -> dict[str, Any]:
        """Read the user's local portfolio summary; quotes are opt-in. Never expose it to another user."""
        return await _read_backend(backend.get_portfolio(include_quotes))

    @server.tool(annotations=read_only, structured_output=True)
    async def get_data_sources(code: FundCode) -> dict[str, Any]:
        """Read per-source quotes, quality and timestamps; endpoint count is not independent upstream coverage."""
        return await _read_backend(backend.get_data_sources(code))

    @server.tool(annotations=read_only, structured_output=True)
    async def get_provider_catalog() -> dict[str, Any]:
        """Discover shared data-contract version, source capabilities, units and known upstream families."""
        return await _read_backend(backend.get_provider_catalog())

    return server
