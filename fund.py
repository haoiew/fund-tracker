# -*- coding: utf-8 -*-
import pandas as pd
import akshare as ak
import numpy as np
import warnings
import requests
import json
import time
import os
import math
from typing import List, Dict, Optional

# --- 网络重试库 ---
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- 可视化库 ---
from rich.console import Console
from rich.table import Table
from rich.progress import track # 进度条
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from pandas.tseries.offsets import DateOffset, Week

# 忽略警告
warnings.filterwarnings("ignore")

# =============================================================================
# ⚙️ 全局配置中心
# =============================================================================
CONFIG = {
    # --- 数据源 ---
    "file_path": "funds.txt",
    "default_funds": [
        '016531', '017436', '018125', '012349', '015916', 
        '160125', '022365', '012709', '519674', '005051'
    ],

    # --- 筛选阈值 ---
    "screen_up":   {"days": 3, "pct": 0.02}, 
    "screen_down": {"days": 3, "pct": 0.02}, 

    # --- 绘图设置 ---
    "plot_mode": 1,   # 1: 累计涨跌幅对比 (含基准), 2: 真实净值子图
    "plot_range": "6M",
    "show_benchmark": True
}

# =============================================================================
# 🛠️ 核心逻辑类
# =============================================================================
class FundTracker:
    def __init__(self):
        self.fund_codes: List[str] = []
        self.fund_names_map: Dict[str, str] = {} 
        
        # --- 网络请求配置 (带重试机制) ---
        self.session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
        self.session.mount('http://', HTTPAdapter(max_retries=retries))
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'http://fund.eastmoney.com/'
        })
        print("基金跟踪器已初始化 (已启用自动重试机制)。")

    def add_funds(self, codes: List[str]):
        new_codes = [str(c) for c in codes if str(c) not in self.fund_codes]
        self.fund_codes.extend(new_codes)
        print(f"成功添加 {len(new_codes)} 只基金。当前共跟踪 {len(self.fund_codes)} 只。")

    def ensure_fund_names(self, console: Console):
        """
        强制补全所有基金名称 (解决 160125 等 LOF 基金无名称的问题)
        """
        unknown_codes = [c for c in self.fund_codes if c not in self.fund_names_map]
        if not unknown_codes:
            return

        # console.print(f"[dim]正在补全 {len(unknown_codes)} 只基金的名称信息...[/dim]")
        
        for code in unknown_codes:
            name = self._fetch_name_strategy(code)
            if name:
                self.fund_names_map[code] = name
    
    def _fetch_name_strategy(self, code: str) -> str:
        """多级策略获取名称"""
        # 策略 1: 尝试 fundgz 接口 (最快，即使没有估值数据，有时也会返回头部信息)
        try:
            ts = int(time.time() * 1000)
            url = f"http://fundgz.1234567.com.cn/js/{code}.js?rt={ts}"
            resp = self.session.get(url, timeout=2)
            text = resp.text.replace("jsonpgz(", "").replace(");", "")
            if text:
                data = json.loads(text)
                if 'name' in data and data['name']:
                    return data['name']
        except: pass

        # 策略 2: Akshare 基础信息接口 (稳健，但稍慢)
        try:
            # 注意: LOF 基金有时需要用 fund_individual_basic_info_em
            df = ak.fund_individual_basic_info_em(symbol=code)
            # 查找包含 "名称" 或 "简称" 的行
            for keyword in ["基金简称", "基金全称", "基金名称"]:
                row = df[df['item'] == keyword]
                if not row.empty:
                    return row['value'].values[0]
        except: pass

        return code # 实在找不到，返回代码

    def get_fund_name(self, code: str) -> str:
        return self.fund_names_map.get(code, code)

    def get_realtime_estimates(self) -> pd.DataFrame:
        """获取实时估值"""
        if not self.fund_codes: return pd.DataFrame()

        print("正在获取实时估值数据 (API 直连 + 重试)...")
        data_list = []
        
        # 使用 track 显示简易进度，因为网络请求可能卡顿
        for code in self.fund_codes:
            try:
                ts = int(time.time() * 1000)
                url = f"http://fundgz.1234567.com.cn/js/{code}.js?rt={ts}"
                resp = self.session.get(url, timeout=3) # 3秒超时+3次重试
                
                text = resp.text.replace("jsonpgz(", "").replace(");", "")
                if not text: continue

                data = json.loads(text)
                
                # 再次确保名称被缓存
                if 'name' in data:
                    self.fund_names_map[code] = data['name']
                    
                data_list.append(data)
                
            except Exception:
                # 即使重试后依然失败，也只能跳过
                pass 
                
        if not data_list:
            return pd.DataFrame()
            
        df = pd.DataFrame(data_list)
        rename_map = {
            'fundcode': '基金代码', 'name': '基金名称', 
            'gz': '估算净值', 'gszzl': '估算涨跌幅', 'gztime': '估值时间'
        }
        df = df.rename(columns=rename_map)
        valid_cols = [c for c in ['基金代码', '基金名称', '估算净值', '估算涨跌幅', '估值时间'] if c in df.columns]
        return df[valid_cols]

    def get_historical_nav(self, code: str) -> pd.DataFrame:
        """获取历史净值"""
        try:
            df = ak.fund_open_fund_info_em(symbol=code, indicator="累计净值走势")
            df['净值日期'] = pd.to_datetime(df['净值日期'])
            df['累计净值'] = pd.to_numeric(df['累计净值'])
            df = df.sort_values('净值日期').reset_index(drop=True)
            df['pct_change'] = df['累计净值'].pct_change().fillna(0)
            return df
        except Exception:
            return pd.DataFrame()

    def _analyze_trend(self, hist_data: pd.DataFrame, direction: str) -> (int, float):
        if hist_data.empty: return 0, 0.0
        target = 1 if direction == 'up' else -1
        days = 0
        changes = []

        for i in range(len(hist_data) - 1, 0, -1):
            chg = hist_data.iloc[i]['pct_change']
            if (chg > 0 and target == 1) or (chg < 0 and target == -1):
                days += 1
                changes.append(chg)
            else:
                break
        
        if days == 0: return 0, 0.0
        total_chg = np.prod([1 + r for r in changes]) - 1
        return days, abs(total_chg)

    def screen_funds(self, direction: str, min_days: int, min_pct: float, console: Console) -> List[Dict]:
        results = []
        console.print(f"\n开始筛选: 连续[bold]{'上涨' if direction=='up' else '下跌'}[/bold] >= {min_days} 天, 或 累计幅度 >= {min_pct*100:.2f}%", style="italic")
        
        for code in self.fund_codes:
            hist = self.get_historical_nav(code)
            if hist.empty: continue

            days, total_chg = self._analyze_trend(hist, direction)
            
            if days >= min_days or total_chg >= min_pct:
                pct_show = round(total_chg * 100, 2)
                name = self.get_fund_name(code) 
                
                results.append({
                    '基金代码': code,
                    '基金名称': name, 
                    '连续天数': days,
                    '累计涨跌幅(%)': pct_show
                })

        return results

# =============================================================================
# 📈 绘图管理类 (含基准对比)
# =============================================================================
class PlotManager:
    @staticmethod
    def setup_font(console):
        try:
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
            plt.rcParams['axes.unicode_minus'] = False 
        except Exception as e:
            console.print(f"[yellow]字体设置警告: {e}[/yellow]")

    @staticmethod
    def get_start_date(range_str: str):
        range_map = {
            '1W': Week(1), '1M': DateOffset(months=1),
            '3M': DateOffset(months=3), '6M': DateOffset(months=6),
            '1Y': DateOffset(years=1)
        }
        return pd.Timestamp.now() - range_map.get(range_str, DateOffset(months=3))

    @staticmethod
    def fetch_benchmark_data(symbol: str, start_date):
        try:
            df = ak.stock_zh_index_daily(symbol=symbol)
            df['date'] = pd.to_datetime(df['date'])
            df = df[df['date'] >= start_date].sort_values('date')
            return df
        except Exception as e:
            print(f"获取基准 {symbol} 失败: {e}")
            return pd.DataFrame()

    @staticmethod
    def plot(tracker, mode: int, range_str: str, show_bench: bool, console: Console):
        if mode == 0: return
        
        console.print(f"\n[bold]📈 正在生成图表 (模式: {mode}, 范围: {range_str})...[/bold]")
        PlotManager.setup_font(console)
        start_date = PlotManager.get_start_date(range_str)
        
        # 1. 准备基金数据
        fund_data = {}
        for code in tracker.fund_codes:
            df = tracker.get_historical_nav(code)
            if not df.empty:
                df = df[df['净值日期'] >= start_date]
                if not df.empty:
                    fund_data[code] = df

        if not fund_data:
            console.print("[red]无可绘图数据[/red]")
            return

        # 2. 准备基准数据
        bench_data = {}
        if mode == 1 and show_bench:
            print("正在获取基准指数 (上证指数, 沪深300)...")
            b_map = {"上证指数": "sh000001", "沪深300": "sh000300"}
            for name, sym in b_map.items():
                b_df = PlotManager.fetch_benchmark_data(sym, start_date)
                if not b_df.empty:
                    bench_data[name] = b_df

        # --- Mode 1: 累计涨跌幅对比 (含基准) ---
        if mode == 1:
            plt.figure(figsize=(14, 8))
            plt.title(f"基金 vs 基准 累计涨跌幅对比 (近 {range_str})", fontsize=16)
            plt.ylabel("累计涨跌幅", fontsize=12)
            
            # A. 画基准
            for name, df in bench_data.items():
                start_val = df['close'].iloc[0]
                pct_val = (df['close'] - start_val) / start_val * 100
                plt.plot(df['date'], pct_val, label=f"[基准] {name}", 
                         linestyle='--', color='black' if name=="上证指数" else "gray", 
                         linewidth=2, alpha=0.8)

            # B. 画基金
            for code, df in fund_data.items():
                start_val = df['累计净值'].iloc[0]
                pct_val = (df['累计净值'] - start_val) / start_val * 100
                name = tracker.get_fund_name(code)
                plt.plot(df['净值日期'], pct_val, label=f"{name}", linewidth=1.5)
            
            plt.gca().yaxis.set_major_formatter(mtick.FormatStrFormatter('%.2f%%'))
            plt.legend(loc='best')
            plt.grid(True, linestyle='--', alpha=0.5)
            plt.tight_layout()
            plt.show()

        # --- Mode 2: 真实净值子图 ---
        elif mode == 2:
            count = len(fund_data)
            cols = 3
            rows = math.ceil(count / cols)
            fig, axes = plt.subplots(rows, cols, figsize=(15, 4 * rows))
            fig.suptitle(f"基金真实累计净值走势 (近 {range_str})", fontsize=16)
            if count == 1: axes = [axes]
            else: axes = axes.flatten()
            
            for i, (code, df) in enumerate(fund_data.items()):
                ax = axes[i]
                name = tracker.get_fund_name(code)
                ax.plot(df['净值日期'], df['累计净值'], color='tab:blue', linewidth=2)
                ax.set_title(f"{name}\n({code})", fontsize=10)
                ax.grid(True, linestyle=':', alpha=0.6)
                ax.tick_params(axis='x', rotation=30)

            if count > 1:
                for j in range(i + 1, len(axes)): axes[j].axis('off')
            
            plt.tight_layout()
            plt.subplots_adjust(top=0.92)
            plt.show()

# =============================================================================
# 🛠️ 辅助工具
# =============================================================================
def load_fund_codes(file_path, default_list):
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return list(set([line.strip() for line in f if line.strip()]))
        except: pass
    return default_list

def print_beautiful_table(console, df, title):
    if df.empty:
        console.print(f"\n  [italic dim]（{title} 无数据）[/italic dim]")
        return
    table = Table(title=title, show_header=True, header_style="bold magenta", border_style="dim", show_lines=False)
    for col in df.columns:
        style = "cyan" if any(x in col for x in ["代码","名称","时间"]) else "green"
        justify = "left" if style=="cyan" else "right"
        table.add_column(col, justify=justify, style=style)
    for row in df.itertuples(index=False):
        table.add_row(*[str(item) if pd.notna(item) else "N/A" for item in row])
    console.print(table)

# =============================================================================
# 🚀 主程序
# =============================================================================
if __name__ == "__main__":
    console = Console()
    tracker = FundTracker()

    # 1. 加载代码
    codes = load_fund_codes(CONFIG["file_path"], CONFIG["default_funds"])
    tracker.add_funds(codes)
    
    # 2. ⚡️ 强制补全名称 (修复 160125 等基金无名称问题)
    tracker.ensure_fund_names(console)
    
    console.print("-" * 30, style="dim")

    # 3. 实时估值 (带重试，减少“消失”情况)
    realtime_df = tracker.get_realtime_estimates()
    print_beautiful_table(console, realtime_df, "📈 基金实时估值")

    console.print("-" * 30, style="dim")

    # 4. 筛选 (名称现在应该都齐全了)
    up_list = tracker.screen_funds('up', CONFIG["screen_up"]["days"], CONFIG["screen_up"]["pct"], console)
    print_beautiful_table(console, pd.DataFrame(up_list), "✅ 满足 [连续上涨] 条件的基金")

    console.print("-" * 30, style="dim")
    
    down_list = tracker.screen_funds('down', CONFIG["screen_down"]["days"], CONFIG["screen_down"]["pct"], console)
    print_beautiful_table(console, pd.DataFrame(down_list), "✅ 满足 [连续下跌] 条件的基金")
    
    console.print("-" * 30, style="dim")

    # 5. 绘图
    PlotManager.plot(
        tracker, 
        mode=CONFIG["plot_mode"], 
        range_str=CONFIG["plot_range"], 
        show_bench=CONFIG["show_benchmark"],
        console=console
    )