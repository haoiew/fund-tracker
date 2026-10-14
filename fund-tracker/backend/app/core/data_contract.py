"""Shared quote contract and provider capabilities; no HTTP, database or MCP imports."""
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
import math
import re
from typing import Any, Dict, List, Literal, Optional

from app.config import settings

CONTRACT_VERSION = "1.0"

SHANGHAI = timezone(timedelta(hours=8))
# 首页与来源对比共用这一顺序；GET/POST、同站镜像不重复登记。
ESTIMATE_SOURCES = ("sina", "tiantian", "dayfund", "fund123")
NAV_SOURCES = ("eastmoney_mobile", "tencent", "eastmoney_lsjz", "pingzhongdata")
DATA_SOURCE_COMPARISON_SOURCES = [(source, priority) for priority, source in enumerate(ESTIMATE_SOURCES + NAV_SOURCES, start=1)]
DATA_SOURCE_METADATA = {
    "tiantian": {
        "display_name": "天天基金盘中估值接口", "short_name": "TTFund",
        "description": "天天基金 H5 FundValuationLast POST 批量接口；部分基金提供盘中估值，未提供估值时保留正式单位净值。只登记一种请求方式。",
    },
    "sina": {
        "display_name": "新浪基金估值", "short_name": "新浪",
        "description": "新浪基金页面使用的 fu 行情；估值与涨跌幅读取其页面脚本指定字段，非基金官方净值，估值精度未验证。公开接口无持续可用性或再分发授权保证。",
    },
    "dayfund": {
        "display_name": "净值估算网", "short_name": "净值估算网",
        "description": "Dayfund 页面公开估值接口，字段按其自身脚本核对。平台模型估值非官方净值，跨市场时效及精度未完整验证，无 SLA 或再分发授权保证。",
    },
    "fund123": {
        "display_name": "数米基金", "short_name": "数米",
        "description": "Fund123 匿名页面使用的分时估值接口；涨跌比例转换为百分数。部分基金无分时点，页面有估值降级标记；无持续开放或再分发授权保证。",
    },
    "eastmoney_mobile": {
        "display_name": "东方财富移动端单位净值", "short_name": "Eastmoney",
        "description": "FundMNFInfo 批量接口，读取 NAV 单位净值和 PDATE 公布日期；不以 ACCNAV 累计净值计价。与天天基金属于同一上游。",
    },
    "tencent": {
        "display_name": "腾讯基金行情", "short_name": "Tencent",
        "description": "腾讯 jj 基金行情提供最新公布净值，不是场内交易价格或盘中估值。",
    },
    "eastmoney_lsjz": {
        "display_name": "东方财富历史净值接口", "short_name": "Eastmoney",
        "description": "f10/lsjz 的最新单位净值及其净值日期、日增长率。",
    },
    "pingzhongdata": {
        "display_name": "东方财富基金页面数据", "short_name": "Eastmoney",
        "description": "基金页面 Data_netWorthTrend 的最新单位净值；累计净值与单位净值保持区分。",
    },
}


def shanghai_now() -> datetime:
    return datetime.now(SHANGHAI)


def _number(value: Any, positive: bool = False) -> Optional[float]:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
        return number if math.isfinite(number) and (not positive or number > 0) else None
    except (ValueError, TypeError):
        return None


def is_current_estimate(update_time: Optional[str], now: Optional[datetime] = None, close_hour: int = 15) -> bool:
    """检查当日、未来时刻和报价延迟；午休、收盘后允许最近交易时段的报价。"""
    if not update_time or not re.search(r"\d{1,2}:\d{2}", update_time):
        return False
    try:
        stamp = datetime.fromisoformat(update_time)
    except ValueError:
        return False
    stamp = stamp.replace(tzinfo=SHANGHAI) if stamp.tzinfo is None else stamp.astimezone(SHANGHAI)
    now = now or shanghai_now()
    now = now.replace(tzinfo=SHANGHAI) if now.tzinfo is None else now.astimezone(SHANGHAI)
    if stamp.date() != now.date() or now.weekday() >= 5 or (stamp - now).total_seconds() > 60:
        return False
    if now.hour < 9 or (now.hour == 9 and now.minute < 30):
        return False
    reference = now
    if (now.hour == 11 and now.minute >= 30) or now.hour == 12:
        reference = now.replace(hour=11, minute=30, second=0, microsecond=0)
    elif now.hour >= close_hour:
        reference = now.replace(hour=close_hour, minute=0, second=0, microsecond=0)
    # 部分跨市场基金在国内收盘后仍更新，接受真实报价时间。
    reference = max(reference, stamp)
    return (reference - stamp).total_seconds() <= settings.ESTIMATE_MAX_AGE_SECONDS


def get_data_source_metadata(source: str) -> Dict[str, Any]:
    spec = PROVIDER_SPECS.get(source)
    if spec is not None:
        return asdict(spec)
    return {"display_name": source or "未知数据源", "short_name": source or "未知",
            "description": "未登记说明的数据源。", "upstream_family": None}


def _classify_data_kind(source: str, update_time: Optional[str]) -> tuple[str, str]:
    if source in ESTIMATE_SOURCES and update_time and re.search(r"\d{1,2}:\d{2}", update_time):
        return "realtime_estimate", "实时估值"
    return "latest_nav", "最新净值"


classify_data_kind = _classify_data_kind


def _unit_nav_conflicts(first_nav, first_date, second_nav, second_date) -> bool:
    return bool(first_date and first_date == second_date and first_nav is not None and second_nav is not None
                and abs(first_nav - second_nav) > 0.00015)


@dataclass
class FundDataResult:
    code: str
    name: Optional[str] = None
    nav: Optional[float] = None
    change_pct: Optional[float] = None
    update_time: Optional[str] = None
    source: str = ""
    error: Optional[str] = None
    fetch_duration_ms: float = 0.0
    data_kind: Optional[str] = None
    previous_nav: Optional[float] = None
    previous_nav_date: Optional[str] = None
    daily_change: Optional[float] = None
    accumulated_nav: Optional[float] = None
    fund_type: Optional[str] = None
    stale_reason: Optional[str] = None
    fetch_started_at: Optional[str] = None
    fetched_at: str = field(default_factory=lambda: shanghai_now().isoformat())
    is_pending: bool = False
    pending_sources: List[str] = field(default_factory=list)
    primary_source_complete: bool = True
    previous_nav_source: Optional[str] = None

    @property
    def is_success(self) -> bool:
        return self.error is None and _number(self.nav, positive=True) is not None

    @property
    def is_realtime(self) -> bool:
        kind = self.data_kind or _classify_data_kind(self.source, self.update_time)[0]
        # 已知港股标的不能在上海 15:00 收盘后把陈旧报价一直视作新鲜。
        close_hour = 16 if any(word in (self.name or "") for word in ("恒生", "港股", "香港", "H股")) else 15
        return self.is_success and kind == "realtime_estimate" and is_current_estimate(self.update_time, close_hour=close_hour)



@dataclass(frozen=True)
class ProviderSpec:
    source: str
    display_name: str
    short_name: str
    description: str
    upstream_family: Optional[str]
    data_kinds: tuple[str, ...]
    supports_batch: bool = False
    price_unit: str = "per_share"
    change_unit: str = "percent"
    native_change_unit: str = "percent"
    timezone: str = "Asia/Shanghai"
    requires_credentials: bool = False


# Family identifies the known serving upstream, not proven model independence.
_PROVIDER_CAPABILITIES = {
    "sina": ("sina", ("realtime_estimate", "latest_nav"), True),
    "tiantian": ("eastmoney", ("realtime_estimate", "latest_nav"), True),
    "dayfund": (None, ("realtime_estimate", "latest_nav"), False),
    "fund123": (None, ("realtime_estimate",), False),
    "eastmoney_mobile": ("eastmoney", ("latest_nav",), True),
    "tencent": ("tencent", ("latest_nav",), False),
    "eastmoney_lsjz": ("eastmoney", ("latest_nav",), False),
    "pingzhongdata": ("eastmoney", ("latest_nav",), False),
}
PROVIDER_SPECS = {
    source: ProviderSpec(source=source, **DATA_SOURCE_METADATA[source],
                         upstream_family=family, data_kinds=kinds, supports_batch=batch,
                         native_change_unit="ratio" if source == "fund123" else "percent")
    for source, (family, kinds, batch) in _PROVIDER_CAPABILITIES.items()
}


def get_provider_catalog() -> dict[str, Any]:
    return {"contract_version": CONTRACT_VERSION,
            "providers": [asdict(PROVIDER_SPECS[source]) for source, _ in DATA_SOURCE_COMPARISON_SOURCES]}


@dataclass(frozen=True)
class QualityWarning:
    code: str
    message: str


@dataclass(frozen=True)
class QuoteQuality:
    contract_version: str
    value_source: Optional[str]
    upstream_family: Optional[str]
    data_kind: str
    price_basis: Literal["unit_nav", "provider_estimate", "inferred_unit_nav", "unavailable"]
    price_unit: str
    currency: Optional[str]
    change_unit: str
    timezone: str
    source_time: Optional[str]
    nav_date: Optional[str]
    nav_source: Optional[str]
    fetched_at: Optional[str]
    assessed_at: str
    availability: Literal["available", "unavailable", "unsupported", "pending"]
    freshness: Literal["current_estimate", "current_reference", "dated_nav", "stale", "unavailable"]
    nav_age_calendar_days: Optional[int]
    warnings: tuple[QualityWarning, ...]
    pending_sources: tuple[str, ...] = ()


def describe_quote_quality(*, source: str, data_kind: str, source_time: Optional[str],
                           nav_date: Optional[str], nav_source: Optional[str],
                           fetched_at: Optional[str], available: bool, is_realtime: bool = False,
                           is_inferred: bool = False, error: Optional[str] = None,
                           stale_reason: Optional[str] = None, fund_type: Optional[str] = None,
                           pending_sources: tuple[str, ...] | list[str] = (),
                           now: Optional[datetime] = None) -> QuoteQuality:
    """Describe semantics and limitations; never select, invent or change a price."""
    now = now or shanghai_now()
    now = now.replace(tzinfo=SHANGHAI) if now.tzinfo is None else now.astimezone(SHANGHAI)
    warnings = []
    age = None
    if nav_date:
        try:
            age = (now.date() - datetime.strptime(nav_date, "%Y-%m-%d").date()).days
            if age < 0:
                age = None
                warnings.append(QualityWarning("invalid_nav_date", "净值日期在未来，不能作为已公布净值。"))
        except (ValueError, TypeError):
            warnings.append(QualityWarning("invalid_nav_date", "无法确认正式净值的所属日期。"))
    if fund_type == "money_market":
        availability = "unsupported"
    else:
        availability = "available" if available else ("pending" if pending_sources else "unavailable")
    value_source = (nav_source or source) if data_kind == "latest_nav" else source
    spec = PROVIDER_SPECS.get(value_source)
    if not available:
        basis, freshness = "unavailable", "unavailable"
        value_source = None
        warnings.append(QualityWarning("pending_source" if availability == "pending" else "missing_value",
                                       "部分来源仍在采集中，本轮结果尚未完整。" if availability == "pending" else
                                       (error or "当前没有可用报价；空值不是零收益或成本价。")))
    elif data_kind == "latest_nav":
        basis, freshness = "unit_nav", "dated_nav"
        warnings.append(QualityWarning("dated_nav", "正式单位净值对应所列净值日，不是盘中估值或场内成交价。"))
    elif is_inferred:
        basis = "inferred_unit_nav"
        freshness = "current_reference" if is_current_estimate(source_time, now=now) else "stale"
        warnings.append(QualityWarning("inferred_quote", "由披露持仓或关联标的外推，未完整计入未披露资产、跨日收益及汇率。"))
    else:
        basis = "provider_estimate"
        freshness = "current_estimate" if is_realtime and is_current_estimate(source_time, now=now) else "stale"
        warnings.append(QualityWarning("provider_estimate", "平台模型估值，非基金管理人确认的正式净值；准确度未经保证。"))
    if freshness == "stale":
        warnings.append(QualityWarning("stale_quote", "报价时刻不满足当前时效要求，不应作为新鲜盘中数据。"))
    if stale_reason:
        warnings.append(QualityWarning("source_limitation", stale_reason))
    if basis in ("provider_estimate", "inferred_unit_nav") and not nav_date:
        warnings.append(QualityWarning("missing_nav_date", "未确认估值基准的完整净值日期，不能据此对齐跨日误差。"))
    if age is not None and age > 1:
        warnings.append(QualityWarning("nav_baseline_age", f"净值基准距请求日 {age} 个自然日；节假日及披露延迟不等于漏失交易收益。"))
    if spec and spec.upstream_family is None:
        warnings.append(QualityWarning("upstream_unverified", "底层数据供应链未核实，不将该接口计作已证明独立的上游。"))
    return QuoteQuality(
        contract_version=CONTRACT_VERSION, value_source=value_source,
        upstream_family=spec.upstream_family if spec else None, data_kind=data_kind,
        price_basis=basis, price_unit="per_share", currency=None, change_unit="percent",
        timezone="Asia/Shanghai", source_time=source_time if source_time and source_time != "--" else None,
        nav_date=nav_date, nav_source=nav_source, fetched_at=fetched_at, assessed_at=now.isoformat(),
        availability=availability, freshness=freshness, nav_age_calendar_days=age,
        warnings=tuple(warnings), pending_sources=tuple(pending_sources),
    )
