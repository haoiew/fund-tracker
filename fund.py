# -*- coding: utf-8 -*-
"""
基金跟踪器 - 命令行版本
"""
import argparse
from rich.console import Console
import pandas as pd

# 从核心模块导入
from fund_core import (
    FundTracker, PlotManager,
    print_realtime_table, print_screen_table,
    load_fund_codes, update_config_from_args,
    CONFIG
)


# =============================================================================
# 🚀 主程序
# =============================================================================
if __name__ == "__main__":
    # ✅ 添加命令行参数支持
    parser = argparse.ArgumentParser(description='基金跟踪器')
    parser.add_argument('--up_days', type=int, default=CONFIG["screen_up"]["days"])
    parser.add_argument('--up_pct', type=float, default=CONFIG["screen_up"]["pct"])
    parser.add_argument('--down_days', type=int, default=CONFIG["screen_down"]["days"])
    parser.add_argument('--down_pct', type=float, default=CONFIG["screen_down"]["pct"])
    parser.add_argument('--plot_mode', type=int, default=CONFIG["plot_mode"])
    parser.add_argument('--plot_range', type=str, default=CONFIG["plot_range"])

    args = parser.parse_args()

    # 使用命令行参数覆盖CONFIG
    config = update_config_from_args(CONFIG.copy(), args)

    console = Console()
    tracker = FundTracker()

    # 1. 加载
    codes = load_fund_codes(config)
    tracker.add_funds(codes)

    # 2. ✅ 静默加载名称
    tracker.ensure_fund_names(console)

    # 3. 实时估值
    realtime_list = tracker.get_realtime_estimates_all(console)
    print_realtime_table(console, realtime_list)

    # 4. 筛选条件说明
    up_cfg = config["screen_up"]
    down_cfg = config["screen_down"]
    console.print(f"\n[bold yellow]📊 筛选条件说明:[/bold yellow]")
    console.print(f"  • 连续上涨: >= {up_cfg['days']} 天 [dim]或[/dim] 累计幅度 >= {up_cfg['pct']*100:.2f}%")
    console.print(f"  • 连续下跌: >= {down_cfg['days']} 天 [dim]或[/dim] 累计幅度 >= {down_cfg['pct']*100:.2f}%\n")

    up_list = tracker.screen_funds('up', up_cfg["days"], up_cfg["pct"], console)
    print_screen_table(console, pd.DataFrame(up_list), "✅ 满足 [连续上涨] 条件的基金")

    down_list = tracker.screen_funds('down', down_cfg["days"], down_cfg["pct"], console)
    print_screen_table(console, pd.DataFrame(down_list), "\n✅ 满足 [连续下跌] 条件的基金")

    # 5. 绘图
    PlotManager.plot(
        tracker,
        mode=config["plot_mode"],
        range_str=config["plot_range"],
        show_bench=config["show_benchmark"],
        console=console
    )
