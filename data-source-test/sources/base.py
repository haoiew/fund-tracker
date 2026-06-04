# -*- coding: utf-8 -*-
"""
数据源抽象基类
定义统一接口，所有数据源适配器实现相同接口
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
import time


@dataclass
class FundDataResult:
    """基金数据结果"""
    code: str                           # 基金代码
    name: Optional[str] = None          # 基金名称
    nav: Optional[float] = None         # 估算净值或实际净值
    change_pct: Optional[float] = None  # 涨跌幅(%)
    update_time: Optional[str] = None   # 数据更新时间
    source_name: str = ""               # 数据源名称
    raw_data: Optional[Dict[str, Any]] = None  # 原始响应数据
    error: Optional[str] = None         # 错误信息
    fetch_duration_ms: float = 0.0      # 获取耗时(毫秒)
    fetched_at: datetime = field(default_factory=datetime.now)  # 获取时间

    @property
    def is_success(self) -> bool:
        return self.error is None and self.nav is not None


class BaseDataSource(ABC):
    """数据源抽象基类"""

    @abstractmethod
    def get_name(self) -> str:
        """获取数据源名称"""
        pass

    @abstractmethod
    def fetch_single(self, code: str) -> FundDataResult:
        """获取单只基金数据"""
        pass

    def fetch_batch(self, codes: List[str]) -> List[FundDataResult]:
        """批量获取基金数据（默认串行）"""
        return [self.fetch_single(c) for c in codes]

    def _create_error_result(self, code: str, error: str, duration_ms: float = 0) -> FundDataResult:
        """创建错误结果"""
        return FundDataResult(
            code=code,
            source_name=self.get_name(),
            error=error,
            fetch_duration_ms=duration_ms
        )

    def _create_success_result(self, code: str, name: str, nav: float,
                                change_pct: Optional[float], update_time: Optional[str],
                                raw_data: Optional[dict], duration_ms: float) -> FundDataResult:
        """创建成功结果"""
        return FundDataResult(
            code=code,
            name=name,
            nav=nav,
            change_pct=change_pct,
            update_time=update_time,
            source_name=self.get_name(),
            raw_data=raw_data,
            fetch_duration_ms=duration_ms
        )
