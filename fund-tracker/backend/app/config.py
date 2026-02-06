# -*- coding: utf-8 -*-
"""
配置文件 - 所有可调参数集中管理
基于统一配置模块，扩展后端特定配置
"""
import os
from typing import List

# --- 导入统一配置模块 ---
try:
    from shared import (
        FundConfig,
        ChartConfig,
        OcrConfig,
        ServerConfig,
        get_fund_config,
        get_chart_config,
        get_ocr_config,
        get_server_config,
    )
    USE_SHARED_CONFIG = True
except ImportError:
    # 如果 shared 模块不可用，使用本地配置
    USE_SHARED_CONFIG = False
    FundConfig = None
    ChartConfig = None
    OcrConfig = None
    ServerConfig = None

# =============================================================================
# 后端特定配置
# =============================================================================
if USE_SHARED_CONFIG:
    # 使用统一配置模块
    fund_config = get_fund_config()
    chart_config = get_chart_config()
    ocr_config = get_ocr_config()
    server_config = get_server_config()
    
    # 别名，保持向后兼容
    settings = server_config
else:
    # 本地配置（向后兼容）
    class Settings:
        # 应用信息
        APP_NAME: str = "基金跟踪器"
        APP_VERSION: str = "2.0.0"
        DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
        
        # 服务器配置
        HOST: str = os.getenv("HOST", "0.0.0.0")
        PORT: int = int(os.getenv("PORT", 8001))
        
        # CORS配置
        CORS_ORIGINS: List[str] = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:8000").split(",")
        
        # 数据库配置
        DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./fundtracker.db")
        
        # Redis配置
        REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        # JWT配置
        SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
        if not SECRET_KEY and not DEBUG:
            raise ValueError("生产环境必须设置 SECRET_KEY 环境变量")
        ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
        
        # 微信配置
        WECHAT_APPID: str = os.getenv("WECHAT_APPID", "")
        WECHAT_SECRET: str = os.getenv("WECHAT_SECRET", "")
    
    # 基金数据配置
    class FundDataConfig:
        DEFAULT_FUNDS: List[str] = [
            '015916', '513630', '012349', '012709', '017436',
            '017093', '016531', '160125', '018125', '015790',
            '007722', '017091', '022365', '012414', '017437',
            '017641', '007721', '501018', '160723', '161226',
            '160416'
        ]
        FUND_FILE_PATH: str = "funds.txt"  # 基金列表文件路径
        SCREEN_UP: dict = {"days": 2, "pct": 0.03}
        SCREEN_DOWN: dict = {"days": 3, "pct": 0.03}
        REALTIME_CACHE_TTL: int = 60
        HISTORY_CACHE_TTL: int = 3600
        FUND_INFO_CACHE_TTL: int = 86400
        REQUEST_TIMEOUT: int = 5
        REQUEST_RETRY_TIMES: int = 3
        DATA_SOURCES: List[str] = [
            "tiantian", "sina_lof", "akshare_lof", "latest_nav"
        ]
        REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        # 预加载和刷新配置
        PRELOAD_ENABLED: bool = True
        PRELOAD_CONCURRENT: int = 5
        REFRESH_INTERVAL_MINUTES: int = 10
        HISTORY_CACHE_DAYS: int = 365 * 2  # 2年
    
    # 图表配置
    class ChartConfig:
        TIME_RANGES: dict = {
            "1W": {"label": "近1周", "days": 7},
            "1M": {"label": "近1月", "days": 30},
            "3M": {"label": "近3月", "days": 90},
            "6M": {"label": "近6月", "days": 180},
            "1Y": {"label": "近1年", "days": 365},
            "ALL": {"label": "全部", "days": 0}
        }
        COLORS = {
            "up": "#ff4d4f", "down": "#52c41a", "primary": "#1890ff",
            "secondary": "#722ed1", "warning": "#faad14", "text": "#262626",
            "text_secondary": "#8c8c8c", "border": "#d9d9d9", "background": "#f5f5f5"
        }
        BENCHMARKS: dict = {
            "sh000001": {"name": "上证指数", "code": "sh000001"},
            "sh000300": {"name": "沪深300", "code": "sh000300"},
            "sz399006": {"name": "创业板指", "code": "sz399006"}
        }
    
    # OCR配置
    class OcrConfig:
        ALLOWED_EXTENSIONS: set = {'.jpg', '.jpeg', '.png', '.bmp'}
        MAX_FILE_SIZE: int = 5 * 1024 * 1024
        OCR_DPI: int = 300
        OCR_LANG: str = "ch_sim+en"
        FUND_CODE_PATTERN: str = r"\b\d{6}\b"
        CONFIDENCE_THRESHOLD: float = 0.6
    
    # 实例化
    settings = Settings()
    fund_config = FundDataConfig()
    chart_config = ChartConfig()
    ocr_config = OcrConfig()
