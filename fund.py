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
from typing import List, Dict, Optional, Any

# --- 网络重试库 ---
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- 可视化库 ---
from rich.console import Console
from rich.table import Table
from rich.text import Text
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
    "plot_mode": 2,
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
        
        # --- ✅ 恢复重试机制 (解决网络不稳定问题) ---
        self.session = requests.Session()
        retries = Retry(
            total=3, 
            backoff_factor=0.5, 
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET"]  # 新版本urllib3使用allowed_methods
        )
        self.session.mount('http://', HTTPAdapter(max_retries=retries))
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'http://fund.eastmoney.com/'
        })
        print("✅ 基金跟踪器已初始化 (已启用自动重试机制)。")

    def add_funds(self, codes: List[str]):
        new_codes = [str(c) for c in codes if str(c) not in self.fund_codes]
        self.fund_codes.extend(new_codes)
        print(f"成功添加 {len(new_codes)} 只基金。当前共跟踪 {len(self.fund_codes)} 只。")

    def ensure_fund_names(self, console: Console):
        """
        ✅ 优化：名称补全策略 - 天天基金 -> 腾讯 -> Akshare
        """
        unknown_codes = [c for c in self.fund_codes if c not in self.fund_names_map]
        if not unknown_codes: return

        with console.status("[bold cyan]正在校对基金名称信息...", spinner="dots"):
            for code in unknown_codes:
                name = self._fetch_name_strategy(code)
                if name and name != code:
                    self.fund_names_map[code] = name
                    console.print(f"  [dim]✓ {code} -> {name}[/dim]")
    
    def _fetch_name_strategy(self, code: str) -> str:
        """
        ✅ 修复：三级名称获取策略
        """
        # 策略 1: 天天基金实时接口 (优先，即使无估值也可能有名称)
        try:
            ts = int(time.time() * 1000)
            url = f"http://fundgz.1234567.com.cn/js/{code}.js?rt={ts}"
            resp = self.session.get(url, timeout=3)
            if resp.status_code == 200 and resp.text:
                text = resp.text.strip().replace("jsonpgz(", "").replace(");", "")
                if text:
                    data = json.loads(text)
                    if 'name' in data and data['name']: 
                        return data['name']
        except: pass

        # 策略 2: 腾讯基金接口 (✅ 修复：专门用于LOF/QDII)
        try:
            url = f"http://qt.gtimg.cn/q=jj{code}"
            resp = self.session.get(url, timeout=3)
            if resp.status_code == 200 and "v_jj" in resp.text:
                # 返回格式示例: v_jj160125="160125~南方香港优选股票~1.0530~..."
                content = resp.text.split('="')[1].strip('";\n')
                parts = content.split('~')
                if len(parts) > 1 and parts[1]: 
                    return parts[1]
        except: pass

        # 策略 3: Akshare 基础信息 (兜底)
        try:
            df = ak.fund_individual_basic_info_em(symbol=code)
            for kw in ["基金简称", "基金全称", "基金名称"]:
                row = df[df['item'] == kw]
                if not row.empty: 
                    name = row['value'].values[0]
                    if name and str(name).strip(): return str(name).strip()
        except: pass

        return code 

    def get_fund_name(self, code: str) -> str:
        return self.fund_names_map.get(code, code)

    def get_realtime_estimates_all(self, console: Console) -> List[Dict]:
        """
        ✅ 修复：获取实时估值 (优化错误处理和名称同步)
        """
        if not self.fund_codes: return []

        results = []
        
        with console.status("[bold green]正在从天天基金获取实时估值...", spinner="dots"):
            for code in self.fund_codes:
                item = {
                    'code': code,
                    'name': self.get_fund_name(code),
                    'gz': None,
                    'gszzl': None,
                    'time': '--',
                    'status': '获取中'
                }
                
                try:
                    ts = int(time.time() * 1000)
                    url = f"http://fundgz.1234567.com.cn/js/{code}.js?rt={ts}"
                    resp = self.session.get(url, timeout=5)
                    
                    if resp.status_code != 200:
                        item['status'] = f'HTTP {resp.status_code}'
                        results.append(item)
                        continue
                    
                    text = resp.text.strip()
                    if not text or text == '':
                        item['status'] = '无数据(API空)'
                        results.append(item)
                        continue
                    
                    # ✅ 修复：更稳健的JSON解析
                    text = text.replace("jsonpgz(", "").replace(");", "").strip()
                    
                    if not text:
                        item['status'] = '无数据(解析空)'
                        results.append(item)
                        continue
                        
                    data = json.loads(text)
                    
                    # 同步名称
                    if 'name' in data and data['name']:
                        self.fund_names_map[code] = data['name']
                        item['name'] = data['name']
                    
                    item['gz'] = data.get('gsz')
                    item['gszzl'] = data.get('gszzl')
                    item['time'] = data.get('gztime', '--')
                    
                    if item['gz'] is None:
                        item['status'] = '非交易时段'
                    else:
                        item['status'] = '正常'
                        
                except requests.exceptions.Timeout:
                    item['status'] = '网络超时'
                except requests.exceptions.RequestException as e:
                    item['status'] = '网络错误'
                except json.JSONDecodeError as e:
                    item['status'] = 'JSON解析失败'
                except Exception as e:
                    item['status'] = f'未知错误'
                
                results.append(item)
        
        return results

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
        """
        ✅ 核心修复：正确返回带符号的涨跌幅
        """
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
        
        # 计算累计涨跌幅
        total_chg = np.prod([1 + r for r in changes]) - 1
        
        # ✅ 关键修复：下跌时返回负值
        if direction == 'down':
            total_chg = -abs(total_chg)
        else:
            total_chg = abs(total_chg)
            
        return days, total_chg

    def screen_funds(self, direction: str, min_days: int, min_pct: float, console: Console) -> List[Dict]:
        results = []
        for code in self.fund_codes:
            hist = self.get_historical_nav(code)
            if hist.empty: continue

            days, total_chg = self._analyze_trend(hist, direction)
            
            # 注意：total_chg现在已经带符号
            if days >= min_days or abs(total_chg) >= min_pct:
                results.append({
                    'code': code,
                    'name': self.get_fund_name(code), 
                    'days': days,
                    'pct': round(total_chg * 100, 2)  # ✅ 保留正负号
                })

        return results

# =============================================================================
# 📈 绘图管理类
# =============================================================================
class PlotManager:
    @staticmethod
    def setup_font(console):
        try:
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', 'PingFang SC']
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
    def fetch_benchmark(symbol: str, start_date):
        try:
            df = ak.stock_zh_index_daily(symbol=symbol)
            df['date'] = pd.to_datetime(df['date'])
            df = df[df['date'] >= start_date].sort_values('date')
            return df
        except: return pd.DataFrame()

    @staticmethod
    def plot(tracker, mode: int, range_str: str, show_bench: bool, console: Console):
        if mode == 0: return
        
        console.print(f"\n[bold]📈 正在生成图表 (模式: {mode}, 范围: {range_str})...[/bold]")
        PlotManager.setup_font(console)
        start_date = PlotManager.get_start_date(range_str)
        
        fund_data = {}
        with console.status("[bold cyan]正在获取历史数据..."):
            for code in tracker.fund_codes:
                df = tracker.get_historical_nav(code)
                if not df.empty:
                    df = df[df['净值日期'] >= start_date]
                    if not df.empty: fund_data[code] = df
        
        if not fund_data:
            console.print("[red]无数据可绘图[/red]")
            return

        # Mode 1
        if mode == 1:
            plt.figure(figsize=(14, 8), constrained_layout=True)
            plt.title(f"基金 vs 基准 累计涨跌幅对比 (近 {range_str})", fontsize=16)
            plt.ylabel("累计涨跌幅", fontsize=12)
            
            if show_bench:
                b_map = {"上证指数": "sh000001", "沪深300": "sh000300"}
                for name, sym in b_map.items():
                    b_df = PlotManager.fetch_benchmark(sym, start_date)
                    if not b_df.empty:
                        start = b_df['close'].iloc[0]
                        val = (b_df['close'] - start) / start * 100
                        plt.plot(b_df['date'], val, label=f"[{name}]", ls='--', color='k' if "上证" in name else 'gray', lw=2, alpha=0.7)

            for code, df in fund_data.items():
                start = df['累计净值'].iloc[0]
                val = (df['累计净值'] - start) / start * 100
                name = tracker.get_fund_name(code)
                plt.plot(df['净值日期'], val, label=f"{name}", lw=1.5)
            
            plt.gca().yaxis.set_major_formatter(mtick.FormatStrFormatter('%.2f%%'))
            plt.legend(loc='upper left', bbox_to_anchor=(1, 1))
            plt.grid(True, ls='--', alpha=0.5)
            plt.show()

        # Mode 2
        elif mode == 2:
            count = len(fund_data)
            cols = 3
            rows = math.ceil(count / cols)
            fig_height = max(4, rows * 3.5)
            
            fig, axes = plt.subplots(rows, cols, figsize=(16, fig_height), constrained_layout=True)
            fig.suptitle(f"基金真实累计净值走势 (近 {range_str})", fontsize=18)
            
            if count == 1: axes = [axes]
            else: axes = axes.flatten()
            
            for i, (code, df) in enumerate(fund_data.items()):
                ax = axes[i]
                name = tracker.get_fund_name(code)
                ax.plot(df['净值日期'], df['累计净值'], color='#1f77b4', lw=2)
                ax.set_title(f"{name}\n({code})", fontsize=11, pad=10)
                ax.grid(True, ls=':', alpha=0.6)
                ax.tick_params(axis='x', rotation=30, labelsize=9)

            if count > 1:
                for j in range(i + 1, len(axes)): axes[j].axis('off')
            plt.show()

# =============================================================================
# 🖥️ 界面渲染 (Rich Table)
# =============================================================================
def print_realtime_table(console, data_list):
    table = Table(title="📈 基金实时估值 (数据源: 天天基金)", show_header=True, header_style="bold magenta", border_style="dim")
    
    table.add_column("基金代码", justify="left", style="cyan")
    table.add_column("基金名称", justify="left", style="white")
    table.add_column("估算净值", justify="right")
    table.add_column("估算涨跌幅", justify="right")
    table.add_column("估值时间", justify="center", style="dim")
    table.add_column("状态/备注", justify="left")

    for item in data_list:
        # ✅ 修复：涨跌幅颜色 (正值红色，负值绿色)
        gszzl = item['gszzl']
        if gszzl is not None:
            try:
                val = float(gszzl)
                if val > 0: 
                    gszzl_styled = Text(f"+{val}%", style="bold red")
                elif val < 0: 
                    gszzl_styled = Text(f"{val}%", style="bold green")
                else: 
                    gszzl_styled = Text(f"{val}%", style="white")
            except:
                gszzl_styled = Text("--", style="dim")
        else:
            gszzl_styled = Text("--", style="dim")
            
        gz_str = f"{item['gz']}" if item['gz'] is not None else "--"
        status_style = "green" if item['status'] == "正常" else "dim yellow"
        
        table.add_row(
            item['code'], 
            item['name'], 
            gz_str, 
            gszzl_styled, 
            item['time'], 
            Text(item['status'], style=status_style)
        )

    console.print(table)

def print_screen_table(console, df, title):
    if df.empty:
        console.print(f"\n  [italic dim]（{title} 无数据）[/italic dim]")
        return
    table = Table(title=title, show_header=True, header_style="bold magenta", border_style="dim", show_lines=False)
    
    table.add_column("基金代码", justify="left", style="cyan")
    table.add_column("基金名称", justify="left")
    table.add_column("连续天数", justify="right")
    table.add_column("累计涨跌幅(%)", justify="right")

    # ✅ 修复：使用 iterrows 并正确显示正负值颜色
    for _, row in df.iterrows():
        pct = row['pct']
        
        # ✅ 关键修复：根据正负值设置颜色
        if pct > 0:
            pct_style = "bold red"
            pct_text = f"+{pct}%"
        elif pct < 0:
            pct_style = "bold green"
            pct_text = f"{pct}%"
        else:
            pct_style = "white"
            pct_text = f"{pct}%"
        
        table.add_row(
            str(row['code']),
            str(row['name']),
            str(row['days']),
            Text(pct_text, style=pct_style)
        )
    console.print(table)

# =============================================================================
# 🚀 主程序
# =============================================================================
if __name__ == "__main__":
    console = Console()
    tracker = FundTracker()

    # 1. 加载
    codes = []
    if os.path.exists(CONFIG["file_path"]):
        with open(CONFIG["file_path"], 'r') as f:
            codes = [l.strip() for l in f if l.strip()]
    else:
        codes = CONFIG["default_funds"]
    tracker.add_funds(codes)
    
    # 2. ✅ 优化：先加载名称，再获取实时数据
    tracker.ensure_fund_names(console)
    
    console.print("-" * 30, style="dim")

    # 3. 实时估值
    realtime_list = tracker.get_realtime_estimates_all(console)
    print_realtime_table(console, realtime_list)

    console.print("-" * 30, style="dim")

    # 4. ✅ 修复：筛选条件描述更清晰
    up_cfg = CONFIG["screen_up"]
    down_cfg = CONFIG["screen_down"]
    console.print(f"\n[bold yellow]📊 筛选条件说明:[/bold yellow]")
    console.print(f"  • 连续上涨: >= {up_cfg['days']} 天 [dim]或[/dim] 累计幅度 >= {up_cfg['pct']*100:.2f}%")
    console.print(f"  • 连续下跌: >= {down_cfg['days']} 天 [dim]或[/dim] 累计幅度 >= {down_cfg['pct']*100:.2f}%\n")
    
    up_list = tracker.screen_funds('up', up_cfg["days"], up_cfg["pct"], console)
    print_screen_table(console, pd.DataFrame(up_list), "✅ 满足 [连续上涨] 条件的基金")

    down_list = tracker.screen_funds('down', down_cfg["days"], down_cfg["pct"], console)
    print_screen_table(console, pd.DataFrame(down_list), "✅ 满足 [连续下跌] 条件的基金")
    
    console.print("-" * 30, style="dim")

    # 5. 绘图
    PlotManager.plot(
        tracker, 
        mode=CONFIG["plot_mode"], 
        range_str=CONFIG["plot_range"], 
        show_bench=CONFIG["show_benchmark"],
        console=console
    )
