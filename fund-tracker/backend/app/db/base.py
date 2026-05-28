# -*- coding: utf-8 -*-
"""
数据库配置 - SQLite only，无外部依赖
"""
import time
from contextlib import contextmanager
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.logger import get_logger

logger = get_logger("database")

# SQLite引擎
logger.info(f"使用 SQLite 数据库: {settings.database_url}")
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=settings.DEBUG
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    """SQLite优化：WAL模式 + 外键约束"""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)

Base = declarative_base()


def get_db():
    """FastAPI依赖注入"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session():
    """同步上下文管理器"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_health() -> dict:
    start_time = time.time()
    try:
        with get_db_session() as db:
            db.execute(text("SELECT 1"))
            db.commit()
        return {
            'status': 'healthy',
            'response_time': round(time.time() - start_time, 3),
            'database_type': 'sqlite'
        }
    except Exception as e:
        logger.error(f"数据库健康检查失败: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'response_time': round(time.time() - start_time, 3)
        }
