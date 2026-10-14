"""显示口径选择。数据采集与推测计算由调用方完成，此处只选择并说明结果。"""
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from app.core.data_source import is_current_estimate, shanghai_now
from app.schemas.fund import FundRealtimeData


def select_quote(
    direct: FundRealtimeData,
    alternatives: Optional[dict[str, Any]] = None,
    view: str = "auto",
    now: Optional[datetime] = None,
) -> FundRealtimeData:
    now = now or shanghai_now()
    official_nav = direct.official_nav
    official_date = direct.official_update_time
    if direct.data_kind == "latest_nav":
        official_nav = official_nav if official_nav is not None else direct.estimate_nav
        official_date = official_date or direct.update_time
    official = {
        "official_nav": official_nav,
        "official_change": direct.official_change,
        "official_update_time": official_date,
        "official_data_kind_label": "正式单位净值",
    }
    settled = now.hour >= 15 and official_date == now.date().isoformat()
    if view == "nav" or (view == "auto" and settled):
        return direct.model_copy(update={
            **official, "estimate_nav": official_nav, "estimate_change": direct.official_change,
            "update_time": official_date or "--", "data_kind": "latest_nav",
            "data_kind_label": "正式单位净值", "status": "正式净值" if official_nav is not None else "暂无正式净值",
            "is_realtime": False, "is_inferred": False, "estimation_details": None,
        })
    if direct.is_realtime and is_current_estimate(direct.update_time, now=now):
        return direct
    if view == "auto" and alternatives and official_nav is not None:
        choices = [
            ("holdings_based_estimate", "holdings_estimate", "披露持仓外推"),
            ("reference_symbol_estimate", "reference_symbol_estimate", "关联标的推测"),
        ]
        for key, kind, label in choices:
            candidate = alternatives.get(key) or {}
            change = candidate.get("weighted_stock_change_pct")
            stamp = candidate.get("update_time")
            if not candidate.get("feasible") or change is None or not is_current_estimate(stamp, now=now):
                continue
            change = Decimal(str(change))
            if not change.is_finite() or change <= -100:
                continue
            return direct.model_copy(update={
                **official, "estimate_nav": (official_nav * (1 + change / 100)).quantize(Decimal("0.0001")),
                "estimate_change": change, "update_time": stamp, "status": label,
                "data_source": kind, "data_source_display_name": label, "data_source_short_name": "Inferred",
                "data_source_description": (
                    f"非官方推测；基准净值日 {official_date or '未知'}，行情时刻 {stamp}，"
                    f"披露持仓日 {candidate.get('position_date') or '不适用'}，"
                    f"已报价资产占基金净值 {candidate.get('quoted_nav_weight_pct') if candidate.get('quoted_nav_weight_pct') is not None else '未知'}%。"
                    "仅应用当日行情变动，基准净值跨日缺口、汇率及未披露资产未完整计价。"
                ),
                "data_kind": kind, "data_kind_label": label, "is_realtime": False,
                "is_inferred": True, "estimation_details": {
                    "method": kind, "baseline_nav": str(official_nav), "baseline_date": official_date,
                    "quote_as_of": stamp, "position_date": candidate.get("position_date"),
                    "quoted_weight_coverage": candidate.get("quoted_weight_coverage"),
                    "quoted_nav_weight_pct": candidate.get("quoted_nav_weight_pct"),
                    "references": candidate.get("references"),
                    "assumption": candidate.get("assumption"),
                    "baseline_alignment": "latest_published_nav_with_current_daily_move",
                    "limitation": "未补齐基准日之后尚未公布的跨日收益，未完整计入汇率及未披露资产",
                },
            })
    return direct.model_copy(update={
        **official, "estimate_nav": None, "estimate_change": None,
        "update_time": "--", "data_kind": "unavailable", "data_kind_label": "暂无可用估值",
        "status": direct.error or "暂无可用估值", "is_realtime": False,
        "is_inferred": False, "estimation_details": None,
    })
