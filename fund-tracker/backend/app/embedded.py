"""Start the existing API inside Android's Python runtime, bound only to loopback."""
import json
import secrets
import socket
import threading
import time
from typing import Any


class LocalTokenGuard:
    """Other apps on the device must not be able to read or change this app's holdings."""

    def __init__(self, app: Any, token: str):
        self.app = app
        self.token = token.encode("ascii")

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["method"] != "OPTIONS":
            supplied = dict(scope.get("headers", [])).get(b"x-fund-tracker-token", b"")
            if not secrets.compare_digest(supplied, self.token):
                body = b'{"code":403,"message":"Forbidden","data":null}'
                await send({"type": "http.response.start", "status": 403,
                            "headers": [(b"content-type", b"application/json")]})
                await send({"type": "http.response.body", "body": body})
                return
        await self.app(scope, receive, send)


_start_lock = threading.Lock()
_server = None
_server_thread = None
_connection = None


def start_backend(timeout_seconds: float = 60) -> str:
    """Called off Android's UI thread after FUND_TRACKER_DATA_DIR has been configured."""
    global _server, _server_thread, _connection
    with _start_lock:
        if _server_thread is not None and _server_thread.is_alive() and _server.started:
            return json.dumps(_connection)
        if _server_thread is not None and _server_thread.is_alive():
            _server.should_exit = True
            _server_thread.join(timeout=8)
            if _server_thread.is_alive():
                raise RuntimeError("The previous embedded API is still shutting down")

        import uvicorn
        from app.main import app
        from app.db.base import Base, engine, check_db_health

        health = check_db_health()
        if health["status"] != "healthy":
            raise RuntimeError("The application's local database could not be opened")
        # Desktop startup logs table errors; a standalone app must not claim readiness on failure.
        Base.metadata.create_all(bind=engine)

        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen(128)
        port = listener.getsockname()[1]
        token = secrets.token_urlsafe(32)
        config = uvicorn.Config(LocalTokenGuard(app, token), host="127.0.0.1", port=port,
                                loop="asyncio", http="h11", ws="none", access_log=False,
                                log_config=None, timeout_graceful_shutdown=5)
        server = uvicorn.Server(config)
        _server = server
        failures = []

        def run():
            try:
                server.run(sockets=[listener])
            except BaseException as exc:
                failures.append(exc)
            finally:
                listener.close()

        _server_thread = threading.Thread(target=run, name="fund-tracker-api", daemon=True)
        _server_thread.start()
        deadline = time.monotonic() + timeout_seconds
        while not server.started:
            if not _server_thread.is_alive():
                raise RuntimeError("The embedded API stopped during startup") from (failures[0] if failures else None)
            if time.monotonic() >= deadline:
                server.should_exit = True
                raise TimeoutError("The embedded API did not become ready in time")
            time.sleep(0.05)
        _connection = {"apiBaseUrl": f"http://127.0.0.1:{port}/api/v1", "accessToken": token}
        return json.dumps(_connection)


def stop_backend() -> None:
    if _server is not None:
        _server.should_exit = True
    if _server_thread is not None:
        _server_thread.join(timeout=8)
