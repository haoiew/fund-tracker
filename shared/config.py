# -*- coding: utf-8 -*-
"""
统一配置模块 - 跨项目共享配置
支持 fund_core.py、fund-tracker、fund-tracker-desktop 共用
"""
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path


# =============================================================================
# 基础配置类
# =============================================================================
@dataclass
class BaseConfig:
    """基础配置类"""
    
    # 应用信息
    APP_NAME: str = "基金跟踪器"
    APP_VERSION: str = "2.0.0"
    
    # 环境检测
    DEBUG: bool = False
    ENV: str = "development"
    
    def __post_init__(self):
        """初始化后处理"""
        # 从环境变量读取 DEBUG
        self.DEBUG = os.getenv("DEBUG", "false").lower() == "true"
        self.ENV = os.getenv("ENV", "development")


# =============================================================================
# 基金数据配置
# =============================================================================
@dataclass
class FundConfig(BaseConfig):
    """基金数据配置"""
    
    # 默认基金列表
    DEFAULT_FUNDS: List[str] = field(default_factory=lambda: [
        '016531', '017436', '018125', '012349', '015916',
        '160125', '022365', '012709', '519674', '005051'
    ])
    
    # 基金代码文件路径
    FUND_FILE_PATH: str = "funds.txt"
    
    # 筛选阈值配置
    SCREEN_UP: Dict[str, Any] = field(default_factory=lambda: {"days": 2, "pct": 0.03})
    SCREEN_DOWN: Dict[str, Any] = field(default_factory=lambda: {"days": 3, "pct": 0.03})
    
    # 缓存时间（秒）
    REALTIME_CACHE_TTL: int = 60
    HISTORY_CACHE_TTL: int = 3600
    FUND_INFO_CACHE_TTL: int = 86400
    
    # 请求超时配置
    REQUEST_TIMEOUT: int = 5
    REQUEST_RETRY_TIMES: int = 3
    
    # 数据源优先级
    DATA_SOURCES: List[str] = field(default_factory=lambda: [
        "tiantian",
        "sina_lof",
        "akshare_lof",
        "latest_nav"
    ])
    
    # 界面显示
    SHOW_NAME_LOADING: bool = False


# =============================================================================
# 图表配置
# =============================================================================
@dataclass
class ChartConfig(BaseConfig):
    """图表配置"""
    
    # 时间范围选项
    TIME_RANGES: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "1W": {"label": "近1周", "days": 7},
        "1M": {"label": "近1月", "days": 30},
        "3M": {"label": "近3月", "days": 90},
        "6M": {"label": "近6月", "days": 180},
        "1Y": {"label": "近1年", "days": 365},
        "ALL": {"label": "全部", "days": 0}
    })
    
    # 图表颜色配置
    COLORS: Dict[str, str] = field(default_factory=lambda: {
        "up": "#ff4d4f",
        "down": "#52c41a",
        "primary": "#1890ff",
        "secondary": "#722ed1",
        "warning": "#faad14",
        "text": "#262626",
        "text_secondary": "#8c8c8c",
        "border": "#d9d9d9",
        "background": "#f5f5f5"
    })
    
    # 基准指数配置
    BENCHMARKS: Dict[str, Dict[str, str]] = field(default_factory=lambda: {
        "sh000001": {"name": "上证指数", "code": "sh000001"},
        "sh000300": {"name": "沪深300", "code": "sh000300"},
        "sz399006": {"name": "创业板指", "code": "sz399006"}
    })


# =============================================================================
# 绘图配置（用于 fund_core.py）
# =============================================================================
@dataclass
class PlotConfig(BaseConfig):
    """绘图配置"""
    
    # 绘图模式: 0-不绘图, 1-对比图, 2-子图
    PLOT_MODE: int = 0
    
    # 时间范围: 1W/1M/3M/6M/1Y
    PLOT_RANGE: str = "1W"
    
    # 是否显示基准
    SHOW_BENCHMARK: bool = True
    
    # 是否显示名称加载过程
    SHOW_NAME_LOADING: bool = False


# =============================================================================
# OCR 配置
# =============================================================================
@dataclass
class OcrConfig(BaseConfig):
    """OCR 配置"""
    
    # 支持的图片格式
    ALLOWED_EXTENSIONS: set = field(default_factory=lambda: {'.jpg', '.jpeg', '.png', '.bmp'})
    MAX_FILE_SIZE: int = 5 * 1024 * 1024  # 5MB
    
    # OCR 识别配置
    OCR_DPI: int = 300
    OCR_LANG: str = "ch_sim+en"
    
    # 基金代码正则表达式
    FUND_CODE_PATTERN: str = r"\b\d{6}\b"
    
    # 置信度阈值
    CONFIDENCE_THRESHOLD: float = 0.6


# =============================================================================
# 服务器配置
# =============================================================================
@dataclass
class ServerConfig(BaseConfig):
    """服务器配置"""
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    
    # CORS 配置
    CORS_ORIGINS: List[str] = field(default_factory=lambda: ["http://localhost:5173", "http://localhost:8000"])
    
    # 数据库配置
    DATABASE_URL: str = "sqlite:///./fundtracker.db"
    
    # Redis 配置
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT 配置
    SECRET_KEY: Optional[str] = None
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7天
    
    # 微信配置
    WECHAT_APPID: str = ""
    WECHAT_SECRET: str = ""
    
    def __post_init__(self):
        """初始化后处理"""
        super().__post_init__()
        
        # 从环境变量读取配置
        self.HOST = os.getenv("HOST", self.HOST)
        self.PORT = int(os.getenv("PORT", str(self.PORT)))
        self.CORS_ORIGINS = os.getenv("CORS_ORIGINS", ",".join(self.CORS_ORIGINS)).split(",")
        self.DATABASE_URL = os.getenv("DATABASE_URL", self.DATABASE_URL)
        self.REDIS_URL = os.getenv("REDIS_URL", self.REDIS_URL)
        self.SECRET_KEY = os.getenv("SECRET_KEY", "")
        self.WECHAT_APPID = os.getenv("WECHAT_APPID", "")
        self.WECHAT_SECRET = os.getenv("WECHAT_SECRET", "")


# =============================================================================
# 配置验证
# =============================================================================
def validate_config(config: BaseConfig) -> List[str]:
    """验证配置，返回错误列表"""
    errors = []
    
    # 验证服务器配置
    if isinstance(config, ServerConfig):
        # 只在非 DEBUG 模式下验证 SECRET_KEY
        if not config.DEBUG and not config.SECRET_KEY:
            errors.append("生产环境必须设置 SECRET_KEY 环境变量")
        
        if config.PORT < 1 or config.PORT > 65535:
            errors.append(f"端口号 {config.PORT} 无效，必须在 1-65535 之间")
    
    # 验证基金配置
    if isinstance(config, FundConfig):
        if not config.DEFAULT_FUNDS:
            errors.append("默认基金列表不能为空")
        
        if not os.path.exists(config.FUND_FILE_PATH):
            errors.append(f"基金文件 {config.FUND_FILE_PATH} 不存在")
    
    return errors


# =============================================================================
# 配置加载器
# =============================================================================
class ConfigLoader:
    """配置加载器"""
    
    _instances: Dict[str, BaseConfig] = {}
    
    @classmethod
    def get_config(cls, config_class: type, name: str = "default") -> BaseConfig:
        """获取配置实例（单例模式）"""
        key = f"{config_class.__name__}_{name}"
        
        if key not in cls._instances:
            config = config_class()
            
            # 验证配置
            errors = validate_config(config)
            if errors:
                raise ValueError(f"配置验证失败: {'; '.join(errors)}")
            
            cls._instances[key] = config
        
        return cls._instances[key]
    
    @classmethod
    def reload(cls):
        """重新加载所有配置"""
        cls._instances.clear()


# =============================================================================
# 便捷访问函数
# =============================================================================
def get_fund_config(name: str = "default") -> FundConfig:
    """获取基金配置"""
    return ConfigLoader.get_config(FundConfig, name)


def get_chart_config(name: str = "default") -> ChartConfig:
    """获取图表配置"""
    return ConfigLoader.get_config(ChartConfig, name)


def get_plot_config(name: str = "default") -> PlotConfig:
    """获取绘图配置"""
    return ConfigLoader.get_config(PlotConfig, name)


def get_server_config(name: str = "default") -> ServerConfig:
    """获取服务器配置"""
    return ConfigLoader.get_config(ServerConfig, name)


def get_ocr_config(name: str = "default") -> OcrConfig:
    """获取 OCR 配置"""
    return ConfigLoader.get_config(OcrConfig, name)


# =============================================================================
# 向后兼容：保持 CONFIG 字典接口
# =============================================================================
def get_legacy_config() -> Dict[str, Any]:
    """获取向后兼容的配置字典（用于 fund_core.py）"""
    fund_config = get_fund_config()
    plot_config = get_plot_config()
    
    return {
        "file_path": fund_config.FUND_FILE_PATH,
        "default_funds": fund_config.DEFAULT_FUNDS,
        "screen_up": fund_config.SCREEN_UP,
        "screen_down": fund_config.SCREEN_DOWN,
        "plot_mode": plot_config.PLOT_MODE,
        "plot_range": plot_config.PLOT_RANGE,
        "show_benchmark": plot_config.SHOW_BENCHMARK,
        "show_name_loading": plot_config.SHOW_NAME_LOADING
    }


# =============================================================================
# 默认配置实例（用于向后兼容）
# =============================================================================
fund_config = get_fund_config()
chart_config = get_chart_config()
plot_config = get_plot_config()
server_config = get_server_config()
ocr_config = get_ocr_config()

# 向后兼容
CONFIG = get_legacy_config()