# -*- coding: utf-8 -*-
import os
from decimal import Decimal
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture(scope="session")
def app_and_engine(tmp_path_factory):
    base_dir = tmp_path_factory.mktemp("fund-tracker-tests")
    os.environ.setdefault("DEBUG", "false")
    os.environ.setdefault("ENV", "test")
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{(base_dir / 'test.db').as_posix()}")
    os.environ.setdefault("SECRET_KEY", "test-secret-key")

    import app.main as app_main

    from app import models
    from app.db.base import Base
    from app.config import settings
    _ = models

    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    # Lifespan and history use module-bound engines/sessions, not get_db overrides.
    # Isolate those paths as well so ordinary pytest never opens the user database.
    from app.db import base as database_module
    from app.services import history_service as history_module
    patcher = pytest.MonkeyPatch()
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    patcher.setattr(app_main, "engine", test_engine)
    patcher.setattr(database_module, "engine", test_engine)
    patcher.setattr(database_module, "SessionLocal", testing_session)
    patcher.setattr(history_module, "SessionLocal", testing_session)

    settings.PRELOAD_ENABLED = False

    # Patch scheduler to no-op
    from app.core.scheduler import scheduler_service
    scheduler_service.start = lambda *a, **kw: None
    scheduler_service.shutdown = lambda *a, **kw: None
    scheduler_service._running = True

    # Patch fund_service with fakes
    from app.services import fund_service as fund_service_module
    from app.schemas.fund import FundRealtimeData

    def fake_get_fund_name(code: str) -> str:
        return f"基金{code}"

    async def fake_get_realtime_data(code: str, view: str = "auto", refresh: bool = False) -> FundRealtimeData:
        return FundRealtimeData(
            code=code,
            name=f"基金{code}",
            estimate_nav=Decimal("1.2345"),
            estimate_change=Decimal("0.50"),
            status="ok",
        )

    async def fake_get_realtime_batch(codes: list[str], view: str = "auto", refresh: bool = False) -> list[FundRealtimeData]:
        return [await fake_get_realtime_data(code) for code in codes]

    _original_get_fund_service = fund_service_module.get_fund_service

    def _patched_get_fund_service():
        svc = _original_get_fund_service()
        svc.get_fund_name = fake_get_fund_name
        svc.get_realtime_data = fake_get_realtime_data
        svc.get_realtime_batch = fake_get_realtime_batch
        return svc

    fund_service_module.get_fund_service = _patched_get_fund_service

    try:
        yield app_main.app, test_engine
    finally:
        patcher.undo()
        test_engine.dispose()


@pytest.fixture(scope="function")
def db_session(app_and_engine) -> Generator[Session, None, None]:
    _app, engine = app_and_engine
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def client(app_and_engine, db_session):
    app, engine = app_and_engine

    from app.db.base import get_db

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)

    async def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def source_manager(monkeypatch):
    """Isolated source tests never reach live providers, including newly added ones."""
    from app.core import data_source

    manager = data_source.DataSourceManager()
    manager._cache.invalidate_pattern("source_snapshot:")

    def unavailable(code, source):
        return data_source.FundDataResult(code=code, source=source, error="test unavailable")

    monkeypatch.setattr(manager._sina, "fetch_batch", lambda codes: [unavailable(c, "sina") for c in codes])
    monkeypatch.setattr(manager._eastmoney, "fetch_tiantian_batch", lambda codes: [unavailable(c, "tiantian") for c in codes])
    monkeypatch.setattr(manager._eastmoney, "fetch_mobile_batch", lambda codes: [unavailable(c, "eastmoney_mobile") for c in codes])
    for source, owner, method in [
        ("tencent", manager._eastmoney, "_try_tencent"),
        ("eastmoney_lsjz", manager._eastmoney, "_try_eastmoney_lsjz"),
        ("pingzhongdata", manager._eastmoney, "_try_pingzhongdata"),
        ("dayfund", manager._dayfund, "fetch_single"), ("fund123", manager._fund123, "fetch_single"),
    ]:
        monkeypatch.setattr(owner, method, lambda code, s=source: unavailable(code, s))
    yield manager
    manager._cache.invalidate_pattern("source_snapshot:")
    manager.close()
