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

    async def fake_get_realtime_data(code: str) -> FundRealtimeData:
        return FundRealtimeData(
            code=code,
            name=f"基金{code}",
            estimate_nav=Decimal("1.2345"),
            estimate_change=Decimal("0.50"),
            status="ok",
        )

    _original_get_fund_service = fund_service_module.get_fund_service

    def _patched_get_fund_service():
        svc = _original_get_fund_service()
        svc.get_fund_name = fake_get_fund_name
        svc.get_realtime_data = fake_get_realtime_data
        return svc

    fund_service_module.get_fund_service = _patched_get_fund_service

    yield app_main.app, test_engine


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
