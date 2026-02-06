# -*- coding: utf-8 -*-
"""
Pytest配置和共享fixture
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.base import SessionLocal, Base, engine


@pytest.fixture(scope="session")
def db_engine():
    """创建测试数据库引擎"""
    # 使用内存数据库进行测试
    from sqlalchemy import create_engine
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=test_engine)
    yield test_engine
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    """创建数据库会话"""
    from sqlalchemy.orm import sessionmaker
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="module")
def client():
    """创建测试客户端"""
    with TestClient(app) as c:
        yield c
