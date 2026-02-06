# -*- coding: utf-8 -*-
"""
启动检查模块
在应用启动时执行各项检查
"""
import os
import sys

# 设置环境变量避免OpenMP警告
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

from app.logger import get_logger

logger = get_logger("startup")


def check_dependencies():
    """检查必要的依赖是否已安装"""
    required_packages = [
        'fastapi',
        'uvicorn',
        'sqlalchemy',
        'pydantic',
        'pandas',
        'numpy',
        'akshare',
        'requests',
    ]

    missing_packages = []

    for package in required_packages:
        try:
            __import__(package)
            logger.debug(f"✓ {package} 已安装")
        except ImportError:
            missing_packages.append(package)
            logger.error(f"✗ {package} 未安装")

    if missing_packages:
        logger.error(f"缺少以下依赖包: {', '.join(missing_packages)}")
        logger.error("请运行: pip install -r requirements.txt")
        return False

    logger.info("✅ 所有依赖检查通过")
    return True


def check_database():
    """检查数据库连接"""
    try:
        from app.db.base import engine
        from sqlalchemy import text

        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()

        logger.info("✅ 数据库连接正常")
        return True
    except Exception as e:
        logger.error(f"✗ 数据库连接失败: {e}")
        return False


def check_redis():
    """检查Redis连接（可选）"""
    try:
        from app.config import settings
        import redis

        if not settings.REDIS_URL:
            logger.info("ℹ️ 未配置Redis，跳过检查")
            return True

        r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        r.ping()
        logger.info("✅ Redis连接正常")
        return True
    except ImportError:
        logger.warning("⚠️ redis包未安装，缓存功能不可用")
        return True  # Redis是可选的
    except Exception as e:
        logger.warning(f"⚠️ Redis连接失败: {e}，缓存功能将不可用")
        return True  # Redis是可选的


def check_ocr_dependencies():
    """检查OCR依赖（可选）"""
    try:
        import easyocr
        logger.info("✅ OCR依赖检查通过")
        return True
    except ImportError:
        logger.warning("⚠️ easyocr未安装，OCR功能将不可用")
        logger.info("   如需使用OCR功能，请运行: pip install easyocr")
        return True  # OCR是可选的


def run_startup_checks():
    """运行所有启动检查"""
    logger.info("🔍 开始启动检查...")

    checks = [
        ("依赖检查", check_dependencies),
        ("数据库检查", check_database),
        ("Redis检查", check_redis),
        ("OCR依赖检查", check_ocr_dependencies),
    ]

    all_passed = True
    for name, check_func in checks:
        logger.info(f"\n📋 {name}...")
        if not check_func():
            all_passed = False
            if name == "依赖检查":
                sys.exit(1)  # 依赖检查失败直接退出

    if all_passed:
        logger.info("\n✅ 所有启动检查通过，应用即将启动")
    else:
        logger.warning("\n⚠️ 部分检查未通过，但应用将继续启动")

    return all_passed


if __name__ == "__main__":
    run_startup_checks()
