# -*- coding: utf-8 -*-
"""
唯一配置源 - 所有配置集中管理
加载顺序：默认值 → .env文件 → 环境变量
"""
import os
from dataclasses import dataclass, field
from typing import List, Dict
from pathlib import Path

from dotenv import load_dotenv

# 加载 .env 文件
_backend_dir = Path(__file__).parent.parent
load_dotenv(_backend_dir / '.env')


@dataclass
class Settings:
    # 应用
    APP_NAME: str = "基金跟踪器"
    APP_VERSION: str = "3.0.0"
    DEBUG: bool = False

    # 服务器
    HOST: str = "127.0.0.1"
    PORT: int = 8001

    # CORS
    CORS_ORIGINS: List[str] = field(default_factory=lambda: [
        "http://localhost:3000", "http://localhost:5173",
        "http://127.0.0.1:3000", "http://127.0.0.1:5173",
        "http://localhost:5174", "http://127.0.0.1:5174",
    ])

    # 数据库（SQLite only）
    DB_PATH: str = "data/fundtracker.db"

    # 基金数据
    FUND_FILE_PATH: str = "funds.txt"
    DEFAULT_FUNDS: List[str] = field(default_factory=lambda: [
        '015916', '513630', '012349', '012709', '017436',
        '017093', '016531', '160125', '018125', '015790',
        '007722', '017091', '022365', '012414', '017437',
        '017641', '007721', '501018', '160723', '161226',
        '160416'
    ])

    # 缓存TTL（秒）
    REALTIME_CACHE_TTL: int = 60
    HISTORY_CACHE_TTL: int = 300
    FUND_INFO_CACHE_TTL: int = 86400
    CHART_CACHE_TTL: int = 300
    SEARCH_CACHE_TTL: int = 300

    # 数据源请求
    REQUEST_TIMEOUT: int = 5
    REQUEST_RETRY: int = 3

    # 筛选阈值
    SCREEN_UP: Dict = field(default_factory=lambda: {"days": 2, "pct": 0.03})
    SCREEN_DOWN: Dict = field(default_factory=lambda: {"days": 3, "pct": 0.03})

    # 图表
    TIME_RANGES: Dict = field(default_factory=lambda: {
        "1W": {"label": "近1周", "days": 7},
        "1M": {"label": "近1月", "days": 30},
        "3M": {"label": "近3月", "days": 90},
        "6M": {"label": "近6月", "days": 180},
        "1Y": {"label": "近1年", "days": 365},
        "ALL": {"label": "全部", "days": 0}
    })

    BENCHMARKS: Dict = field(default_factory=lambda: {
        "sh000001": {"name": "上证指数", "code": "sh000001"},
        "sh000300": {"name": "沪深300", "code": "sh000300"},
        "sz399006": {"name": "创业板指", "code": "sz399006"}
    })

    # 调度器
    REFRESH_INTERVAL_MINUTES: int = 10
    PRELOAD_ENABLED: bool = True
    HISTORY_CACHE_DAYS: int = 730

    def __post_init__(self):
        self.DEBUG = os.getenv("DEBUG", "false").lower() == "true" or self.DEBUG
        self.HOST = os.getenv("HOST", self.HOST)
        self.PORT = int(os.getenv("PORT", str(self.PORT)))

        # 解析 .env 中的基金列表
        env_funds = os.getenv("DEFAULT_FUNDS")
        if env_funds:
            self.DEFAULT_FUNDS = [f.strip() for f in env_funds.split(",") if f.strip()]

        # Ensure DB directory exists once at init time
        db_path = _backend_dir / self.DB_PATH
        db_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def database_url(self) -> str:
        db_path = _backend_dir / self.DB_PATH
        return f"sqlite:///{db_path.as_posix()}"

    @property
    def fund_file_abs_path(self) -> str:
        return str(_backend_dir / self.FUND_FILE_PATH)


# 全局单例
settings = Settings()
