"""Desktop configuration only; never read backend .env files or user databases."""
from dataclasses import dataclass
import ipaddress
import math
import os
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Settings:
    api_url: str = "http://127.0.0.1:8001/api/v1"
    timeout_seconds: float = 65.0

    def __post_init__(self):
        try:
            parsed = urlsplit(self.api_url)
            host = parsed.hostname
            port = parsed.port
            loopback = host == "localhost" or (host is not None and ipaddress.ip_address(host).is_loopback)
        except ValueError:
            raise ValueError("FUND_TRACKER_API_URL must use a localhost/loopback address") from None
        if (parsed.scheme not in ("http", "https") or not loopback or parsed.username or parsed.password
                or parsed.query or parsed.fragment or parsed.path.rstrip("/") != "/api/v1"
                or (port is not None and not 1 <= port <= 65535)):
            raise ValueError("FUND_TRACKER_API_URL must be a loopback HTTP(S) URL ending in /api/v1, without credentials")
        if not math.isfinite(self.timeout_seconds) or not 1 <= self.timeout_seconds <= 120:
            raise ValueError("FUND_TRACKER_MCP_TIMEOUT must be between 1 and 120 seconds")
        object.__setattr__(self, "api_url", self.api_url.rstrip("/"))

    @classmethod
    def from_env(cls, *, api_url: str | None = None, timeout_seconds: float | None = None):
        return cls(api_url=api_url if api_url is not None else os.environ.get("FUND_TRACKER_API_URL", cls.api_url),
                   timeout_seconds=(timeout_seconds if timeout_seconds is not None else
                                    float(os.environ.get("FUND_TRACKER_MCP_TIMEOUT", cls.timeout_seconds))))
