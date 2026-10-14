"""Default mode is stdio only. Configuration output is an explicit separate command."""
import argparse
import json
from pathlib import Path
import sys

from .config import Settings


def main():
    parser = argparse.ArgumentParser(description="Desktop-only, read-only Fund Tracker stdio MCP server")
    parser.add_argument("--api-url", help="Loopback backend API URL, default FUND_TRACKER_API_URL or :8001/api/v1")
    parser.add_argument("--timeout", type=float, help="Backend read timeout in seconds (1..120)")
    parser.add_argument("--print-client-config", action="store_true", help="Print exact config for this interpreter and exit")
    args = parser.parse_args()
    try:
        settings = Settings.from_env(api_url=args.api_url, timeout_seconds=args.timeout)
    except ValueError as exc:
        parser.error(str(exc))
    if args.print_client_config:
        entrypoint = Path(__file__).resolve().parents[1] / "run.py"
        print(json.dumps({"mcpServers": {"fund-tracker": {
            "command": sys.executable, "args": ["-B", str(entrypoint)],
            "env": {"FUND_TRACKER_API_URL": settings.api_url,
                    "FUND_TRACKER_MCP_TIMEOUT": str(settings.timeout_seconds)},
        }}}, ensure_ascii=False, indent=2))
        return
    from .server import create_server
    create_server(settings).run(transport="stdio")


if __name__ == "__main__":
    main()
