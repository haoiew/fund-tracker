"""The Android API shares the real services and keeps its data in private storage."""
import httpx
import pytest
import os
import subprocess
import sys
from app.config import Settings
from app.embedded import LocalTokenGuard


def test_android_data_directory_does_not_write_next_to_packaged_source(tmp_path, monkeypatch):
    monkeypatch.setenv("FUND_TRACKER_DATA_DIR", str(tmp_path))
    settings = Settings()
    assert settings.runtime_dir == tmp_path
    assert settings.database_url == f"sqlite:///{(tmp_path / 'data/fundtracker.db').as_posix()}"
    assert settings.fund_file_abs_path == str(tmp_path / "funds.txt")
    assert (tmp_path / "data").is_dir()


def test_real_embedded_startup_uses_an_isolated_database_and_random_authenticated_port(tmp_path):
    # A separate process avoids the desktop app/config singleton and the user's DB.
    script = """
import json, sqlite3, requests
from app.embedded import start_backend, stop_backend
from app.config import settings
try:
    connection = json.loads(start_backend())
    assert json.loads(start_backend()) == connection
    url = connection['apiBaseUrl'] + '/system/health'
    assert requests.get(url, timeout=5).status_code == 403
    result = requests.get(url, headers={'X-Fund-Tracker-Token': connection['accessToken']}, timeout=5)
    assert result.status_code == 200, result.text
    assert result.json()['data']['status'] == 'healthy'
    with sqlite3.connect(str(settings.runtime_dir / settings.DB_PATH)) as db:
        assert db.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0] > 0
finally:
    stop_backend()
"""
    env = {**os.environ, "FUND_TRACKER_DATA_DIR": str(tmp_path)}
    result = subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, text=True, timeout=35)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.asyncio
async def test_embedded_api_rejects_requests_without_its_per_process_token():
    from fastapi import FastAPI
    inner = FastAPI()

    @inner.get("/holdings")
    def holdings():
        return {"items": []}

    guarded = LocalTokenGuard(inner, "test-only-token")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=guarded), base_url="http://local.test") as client:
        assert (await client.get("/holdings")).status_code == 403
        assert (await client.get("/holdings", headers={"X-Fund-Tracker-Token": "wrong"})).status_code == 403
        response = await client.get("/holdings", headers={"X-Fund-Tracker-Token": "test-only-token"})
        assert response.status_code == 200
        assert response.json() == {"items": []}
