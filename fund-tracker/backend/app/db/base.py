# -*- coding: utf-8 -*-
"""
数据库基础配置 - 支持PostgreSQL和SQLite
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# 检测数据库URL类型
database_url = settings.DATABASE_URL

# 如果是PostgreSQL但 psycopg2/psycopg 未安装，自动切换到SQLite
if database_url.startswith('postgresql'):
    try:
        # 尝试导入 psycopg
        import psycopg
    except ImportError:
        try:
            # 尝试导入 psycopg2
            import psycopg2
        except ImportError:
            print("⚠️ PostgreSQL驱动未安装，自动切换到SQLite内存数据库")
            database_url = "sqlite:///:memory:"

# 创建数据库引擎
if database_url.startswith('sqlite'):
    # SQLite 配置
    engine = create_engine(
        database_url, 
        connect_args={"check_same_thread": False},
        pool_pre_ping=True
    )
else:
    # PostgreSQL 配置
    engine = create_engine(database_url, pool_pre_ping=True)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 声明基类
Base = declarative_base()

# 依赖注入函数
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
