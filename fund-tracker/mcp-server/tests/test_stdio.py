"""Real stdio protocol subprocess against an isolated test HTTP endpoint (no production fake data)."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import sys
import threading

import pytest
from mcp import Client, StdioServerParameters


@pytest.mark.asyncio
async def test_stdio_entrypoint_handshake_discovery_and_tool_call():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            assert self.path == "/api/v1/funds/providers"
            body = json.dumps({"code": 200, "data": {"contract_version": "1.0", "providers": []}}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    api = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=api.serve_forever, daemon=True)
    thread.start()
    entrypoint = Path(__file__).resolve().parents[1] / "run.py"
    params = StdioServerParameters(command=sys.executable, args=["-B", str(entrypoint)],
                                   env={"FUND_TRACKER_API_URL": f"http://127.0.0.1:{api.server_port}/api/v1"})
    try:
        async with Client(params, read_timeout_seconds=15) as client:
            tools = await client.list_tools()
            assert len(tools.tools) == 6
            result = await client.call_tool("get_provider_catalog", {})
            assert not result.is_error
            assert result.structured_content["contract_version"] == "1.0"
            forbidden = await client.call_tool("delete_portfolio", {"id": 1})
            assert forbidden.is_error
    finally:
        api.shutdown()
        api.server_close()
        thread.join(timeout=3)


def test_configuration_command_is_separate_json_and_uses_an_absolute_entrypoint():
    entrypoint = Path(__file__).resolve().parents[1] / "run.py"
    result = subprocess.run([sys.executable, "-B", str(entrypoint), "--print-client-config"],
                            capture_output=True, text=True, check=True, timeout=10)
    config = json.loads(result.stdout)["mcpServers"]["fund-tracker"]
    assert config["command"] == sys.executable
    assert config["args"] == ["-B", str(entrypoint)]
    assert "127.0.0.1" in config["env"]["FUND_TRACKER_API_URL"]
