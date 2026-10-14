"""All sources start together; source priority, not response speed, selects the quote."""
import asyncio
import threading
from datetime import datetime

import pytest

from app.core import data_contract
from app.core import data_source


@pytest.fixture
def manager(monkeypatch):
    monkeypatch.setattr(data_contract, "shanghai_now", lambda: datetime(2026, 10, 14, 14, 5, tzinfo=data_source.SHANGHAI))
    monkeypatch.setattr(data_source, "DATA_SOURCE_COMPARISON_SOURCES", [("sina", 1), ("tiantian", 2)])
    instance = data_source.DataSourceManager()
    instance._cache.invalidate_pattern("source_snapshot:")
    yield instance
    instance._cache.invalidate_pattern("source_snapshot:")
    instance.close()


def quote(code, source, nav=1.01):
    return data_source.FundDataResult(code=code, name="测试基金", nav=nav, source=source,
                                      data_kind="realtime_estimate", update_time="2026-10-14 14:00")


@pytest.mark.asyncio
async def test_sources_start_concurrently_and_prefer_sina_even_when_tiantian_has_a_quote(manager, monkeypatch):
    started = threading.Barrier(2)
    calls = []

    def fetch(source, codes):
        calls.append((source, list(codes)))
        started.wait(timeout=1)
        return [quote(code, source) for code in codes]

    monkeypatch.setattr(manager._sina, "fetch_batch", lambda codes: fetch("sina", codes))
    monkeypatch.setattr(manager._eastmoney, "fetch_tiantian_batch", lambda codes: fetch("tiantian", codes))
    rows = await manager.fetch_batch(["012414", "015916", "012414"])
    assert sorted(calls) == [("sina", ["012414", "015916"]), ("tiantian", ["012414", "015916"])]
    assert [row.source for row in rows] == ["sina"] * 3


def test_priority_has_one_tiantian_and_sina_first():
    sources = [source for source, _ in data_source.DATA_SOURCE_COMPARISON_SOURCES]
    assert sources[0] == "sina"
    assert sources.count("tiantian") == 1
    assert len(sources) == len(set(sources))


@pytest.mark.asyncio
async def test_completion_order_does_not_override_priority(manager, monkeypatch):
    completed = threading.Event()

    def sina(codes):
        assert completed.wait(timeout=1)
        return [quote(c, "sina", 1.02) for c in codes]

    def tiantian(codes):
        completed.set()
        return [quote(c, "tiantian", 1.01) for c in codes]

    monkeypatch.setattr(manager._sina, "fetch_batch", sina)
    monkeypatch.setattr(manager._eastmoney, "fetch_tiantian_batch", tiantian)
    row = await manager.fetch_single("012414")
    assert row.source == "sina" and row.nav == 1.02


@pytest.mark.asyncio
async def test_refresh_reloads_all_sources_but_auto_and_comparison_reuse_snapshot(manager, monkeypatch):
    calls = []

    async def fetch(source, codes, on_results=None):
        calls.append((source, list(codes)))
        return [quote(c, source) for c in codes]

    monkeypatch.setattr(manager, "_fetch_source_batch", fetch)
    await manager.fetch_batch(["012414", "015916"])
    await manager.fetch_batch(["015916"])
    comparison = await manager.compare_sources("012414")
    assert comparison["best_source"] == "sina" and len(calls) == 2
    await manager.fetch_batch(["012414", "015916"], refresh=True)
    assert calls == [("sina", ["012414", "015916"]), ("tiantian", ["012414", "015916"])] * 2


@pytest.mark.asyncio
async def test_overlapping_requests_share_pending_sources_and_cancellation_is_isolated(manager, monkeypatch):
    reached, release = asyncio.Event(), asyncio.Event()
    calls = []

    async def fetch(source, codes, on_results=None):
        calls.append(source)
        if len(calls) == 2:
            reached.set()
        await release.wait()
        return [quote(c, source) for c in codes]

    monkeypatch.setattr(manager, "_fetch_source_batch", fetch)
    first = asyncio.create_task(manager.fetch_batch(["012414"], refresh=True))
    await reached.wait()
    first.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first
    second = asyncio.create_task(manager.compare_sources("012414"))
    release.set()
    result = await second
    assert calls == ["sina", "tiantian"] and result["best_source"] == "sina"


@pytest.mark.asyncio
async def test_every_registered_source_starts_without_waiting_for_failure(source_manager, monkeypatch):
    barrier = threading.Barrier(len(data_source.DATA_SOURCE_COMPARISON_SOURCES))
    calls = []

    def fetch(source, codes):
        calls.append(source)
        barrier.wait(timeout=2)
        if source == "sina":
            raise TimeoutError("private request details must not leak")
        return [quote(c, source) for c in codes]

    monkeypatch.setattr(data_contract, "shanghai_now", lambda: datetime(2026, 10, 14, 14, 5, tzinfo=data_source.SHANGHAI))
    for source, owner, method in [
        ("sina", source_manager._sina, "fetch_batch"),
        ("tiantian", source_manager._eastmoney, "fetch_tiantian_batch"),
        ("eastmoney_mobile", source_manager._eastmoney, "fetch_mobile_batch"),
    ]:
        monkeypatch.setattr(owner, method, lambda codes, s=source: fetch(s, codes))
    for source, owner, method in [
        ("dayfund", source_manager._dayfund, "fetch_single"),
        ("fund123", source_manager._fund123, "fetch_single"),
        ("tencent", source_manager._eastmoney, "_try_tencent"),
        ("eastmoney_lsjz", source_manager._eastmoney, "_try_eastmoney_lsjz"),
        ("pingzhongdata", source_manager._eastmoney, "_try_pingzhongdata"),
    ]:
        monkeypatch.setattr(owner, method, lambda code, s=source: fetch(s, [code])[0])
    row = await source_manager.fetch_single("015916")
    assert row.source == "tiantian"
    assert set(calls) == {s for s, _ in data_source.DATA_SOURCE_COMPARISON_SOURCES}
    comparison = await source_manager.compare_sources("015916")
    assert comparison["sources"][0]["error"] == "请求失败: TimeoutError"


@pytest.mark.asyncio
@pytest.mark.parametrize("winning_source", ["dayfund", "fund123"])
async def test_lower_priority_provider_precedes_local_inference(source_manager, monkeypatch, winning_source):
    monkeypatch.setattr(data_contract, "shanghai_now", lambda: datetime(2026, 10, 14, 14, 5, tzinfo=data_source.SHANGHAI))
    owner = source_manager._dayfund if winning_source == "dayfund" else source_manager._fund123
    monkeypatch.setattr(owner, "fetch_single", lambda code: quote(code, winning_source))
    row = await source_manager.fetch_single("015916")
    assert row.source == winning_source and row.is_realtime


@pytest.mark.asyncio
async def test_slow_single_code_does_not_discard_other_completed_quotes(source_manager, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SOURCE_BATCH_TIMEOUT", 0.05)
    release = threading.Event()

    def fetch(code):
        if code == "015916":
            release.wait(timeout=1)
        return quote(code, "dayfund")

    monkeypatch.setattr(source_manager._dayfund, "fetch_single", fetch)
    try:
        first, slow = await source_manager._fetch_source_batch("dayfund", ["012414", "015916"])
        assert first.nav == 1.01 and first.error is None
        assert not slow.is_success and "超时" in slow.error
    finally:
        release.set()


@pytest.mark.asyncio
async def test_hong_kong_quotes_do_not_use_shanghai_close_to_hide_age(source_manager, monkeypatch):
    monkeypatch.setattr(data_contract, "shanghai_now", lambda: datetime(2026, 10, 14, 15, 30, tzinfo=data_source.SHANGHAI))
    official = data_source.FundDataResult(code="012349", name="天弘恒生科技ETF联接C", source="tiantian",
                                         nav=.56, update_time="2026-10-13", data_kind="latest_nav")
    stale = data_source.FundDataResult(code="012349", source="dayfund", nav=.57, update_time="2026-10-14 14:50",
                                      data_kind="realtime_estimate")
    monkeypatch.setattr(source_manager._eastmoney, "fetch_tiantian_batch", lambda codes: [official])
    monkeypatch.setattr(source_manager._dayfund, "fetch_single", lambda code: stale)
    row = await source_manager.fetch_single("012349")
    assert row.data_kind == "latest_nav" and not row.is_realtime
    comparison = await source_manager.compare_sources("012349")
    assert comparison["realtime_sources"] == 0


@pytest.mark.asyncio
async def test_sina_keeps_independent_nav_when_its_estimate_is_missing(source_manager, monkeypatch):
    payload = 'var hq_str_f_015916="永赢医药创新智选混合发起C,1.5845,1.5845,1.6017,2026-10-13,29.407";'
    rows = data_source.SinaFundAdapter().parse_response(["015916"], payload)
    monkeypatch.setattr(source_manager._sina, "fetch_batch", lambda codes: rows)
    row = await source_manager.fetch_single("015916")
    comparison = await source_manager.compare_sources("015916")
    assert row.data_kind == "latest_nav" and row.previous_nav_date == "2026-10-13"
    assert comparison["best_source"] == "sina" and comparison["sources"][0]["is_available"]
    assert comparison["realtime_sources"] == 0
