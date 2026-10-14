"""Progressive snapshots: primary completion and background completion are separate."""
import asyncio
from datetime import datetime
import pytest
from app.core import data_contract
from app.core import data_source


def quote(code, source):
    return data_source.FundDataResult(code=code, name="测试基金", source=source, nav=1.01,
        change_pct=1.0, update_time="2026-10-14 14:04", data_kind="realtime_estimate")


@pytest.fixture
async def manager(monkeypatch):
    monkeypatch.setattr(data_contract, "shanghai_now", lambda: datetime(2026, 10, 14, 14, 5, tzinfo=data_source.SHANGHAI))
    monkeypatch.setattr(data_source, "DATA_SOURCE_COMPARISON_SOURCES", [("sina", 1), ("tiantian", 2)])
    result = data_source.DataSourceManager()
    result._cache.invalidate_pattern("source_snapshot:")
    yield result
    await result.wait_for_pending()
    result._cache.invalidate_pattern("source_snapshot:")
    result.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("primary_success", [True, False])
async def test_primary_returns_without_waiting_for_backup(manager, monkeypatch, primary_success):
    release, calls = asyncio.Event(), []
    async def fetch(source, codes, on_results=None):
        calls.append(source)
        if source != "sina":
            await release.wait()
        return [quote(c, source) if source != "sina" or primary_success else
                data_source.FundDataResult(code=c, source=source, error="confirmed unavailable") for c in codes]
    monkeypatch.setattr(manager, "_fetch_source_batch", fetch)
    try:
        first = await asyncio.wait_for(manager.fetch_single("015916", refresh=True, wait_all=False), .2)
        assert first.primary_source_complete is True and first.pending_sources == ["tiantian"]
        assert first.source == ("sina" if primary_success else "unknown")
        comparison = await manager.compare_sources("015916", wait_all=False)
        assert comparison["sources"][1]["is_pending"] and comparison["sources"][1]["error"] is None
        await manager.fetch_single("015916", wait_all=False)
        assert calls == ["sina", "tiantian"]
    finally:
        release.set()
    await manager.wait_for_pending()
    final = await manager.fetch_single("015916", wait_all=False)
    assert final.pending_sources == [] and final.source == ("sina" if primary_success else "tiantian")


@pytest.mark.asyncio
async def test_fast_backup_is_visible_then_replaced_by_higher_priority_primary(manager, monkeypatch):
    release = asyncio.Event()
    async def fetch(source, codes, on_results=None):
        if source == "sina":
            await release.wait()
        return [quote(c, source) for c in codes]
    monkeypatch.setattr(manager, "_fetch_source_batch", fetch)
    try:
        first = await asyncio.wait_for(manager.fetch_single("015916", wait_all=False), .2)
        assert first.source == "tiantian" and first.primary_source_complete is False
        assert first.pending_sources == ["sina"]
    finally:
        release.set()
    await manager.wait_for_pending()
    final = await manager.fetch_single("015916", wait_all=False)
    assert final.source == "sina" and final.primary_source_complete is True


@pytest.mark.asyncio
async def test_partial_codes_from_one_source_are_published_immediately(manager, monkeypatch):
    release = asyncio.Event()
    async def fetch(source, codes, on_results=None):
        if source == "sina":
            first = quote(codes[0], source)
            on_results([first])
            await release.wait()
            return [first, quote(codes[1], source)]
        await release.wait()
        return [quote(c, source) for c in codes]
    monkeypatch.setattr(manager, "_fetch_source_batch", fetch)
    try:
        first = await asyncio.wait_for(manager.fetch_batch(["012414", "015916"], wait_all=False), .2)
        assert first[0].source == "sina" and first[0].primary_source_complete
        assert first[1].nav is None and not first[1].primary_source_complete
    finally:
        release.set()


@pytest.mark.asyncio
async def test_single_code_adapter_publishes_before_its_other_codes_finish(manager, monkeypatch):
    import threading
    release, published = threading.Event(), asyncio.Event()
    rows = []
    def fetch(code):
        if code == "015916":
            release.wait(timeout=2)
        return quote(code, "dayfund")
    def publish(batch):
        rows.extend(batch)
        published.set()
    monkeypatch.setattr(manager._dayfund, "fetch_single", fetch)
    task = asyncio.create_task(manager._fetch_source_batch("dayfund", ["012414", "015916"], publish))
    try:
        await asyncio.wait_for(published.wait(), .5)
        assert rows[0].code == "012414" and not task.done()
    finally:
        release.set()
        await task


@pytest.mark.asyncio
async def test_auto_does_not_infer_while_an_estimate_provider_is_pending(monkeypatch):
    from decimal import Decimal
    from app.schemas.fund import FundRealtimeData
    from app.services.fund_service import FundService
    service = FundService()
    async def unexpected(*args, **kwargs):
        pytest.fail("inference ran before all estimate providers returned")
    monkeypatch.setattr(service, "get_realtime_alternatives", unexpected)
    direct = FundRealtimeData(code="015916", name="基金", official_nav=Decimal("1.2"),
        official_update_time="2026-10-13", data_kind="unavailable", pending_sources=["fund123"])
    result = await service._select_display_quote(direct)
    assert result.estimate_nav is None and not result.is_inferred and result.pending_sources == ["fund123"]
