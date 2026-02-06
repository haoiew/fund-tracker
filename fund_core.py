# -*- coding: utf-8 -*-
"""
基金跟踪器核心模块
包含 FundTracker 和 PlotManager 类，供 fund.py、fund_main.py、fund_gui.py 共用
"""
import argparse
import pandas as pd
import akshare as ak
import numpy as np
import warnings
import requests
import json
import time
import os
import math
from typing import List, Dict, Optional, Any, Tuple

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

# --- 统一配置模块 ---
try:
    from shared import CONFIG
except ImportError:
    # 如果 shared 模块不可用，使用默认配置
    CONFIG = {
        "file_path": "funds.txt",
        "default_funds": [
            '016531', '017436', '018125', '012349', '015916',
            '160125', '022365', '012709', '519674', '005051'
        ],
        "screen_up": {"days": 2, "pct": 0.03},
        "screen_down": {"days": 3, "pct": 0.03},
        "plot_mode": 0,
        "plot_range": "1W",
        "show_benchmark": True,
        "show_name_loading": False
    }

# ✅ 禁用进度条显示
os.environ['TQDM_DISABLE'] = '1'  # 禁用tqdm进度条
warnings.filterwarnings("ignore")

# =============================================================================
# ⚙️ 全局配置中心（从统一配置模块导入）
# =============================================================================
# CONFIG 已从 shared 模块导入，保持向后兼容


# =============================================================================
# 🛠️ 核心逻辑类
# =============================================================================
class FundTracker:
    """基金跟踪器核心类"""

    def __init__(self):
        self.fund_codes: List[str] = []
        self.fund_names_map: Dict[str, str] = {}

        # --- 恢复重试机制 ---
        self.session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        self.session.mount('http://', HTTPAdapter(max_retries=retries))
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'http://fund.eastmoney.com/'
        })

    def add_funds(self, codes: List[str]):
        """添加基金代码到跟踪列表"""
        new_codes = [str(c) for c in codes if str(c) not in self.fund_codes]
        self.fund_codes.extend(new_codes)
        print(f"\n✅ 基金跟踪器已初始化，成功添加 {len(self.fund_codes)} 只基金。")

    def ensure_fund_names(self, console: Console):
        """
        ✅ 优化：静默模式名称补全
        """
        unknown_codes = [c for c in self.fund_codes if c not in self.fund_names_map]
        if not unknown_codes:
            return

        show_progress = CONFIG.get("show_name_loading", False)

        if show_progress:
            with console.status("[bold cyan]正在校对基金名称信息...", spinner="dots"):
                for code in unknown_codes:
                    name = self._fetch_name_strategy(code)
                    if name and name != code:
                        self.fund_names_map[code] = name
                        console.print(f"  [dim]✓ {code} -> {name}[/dim]")
        else:
            # ✅ 静默模式：不显示加载过程
            for code in unknown_codes:
                name = self._fetch_name_strategy(code)
                if name and name != code:
                    self.fund_names_map[code] = name

    def _fetch_name_strategy(self, code: str) -> str:
        """三级名称获取策略"""
        # 策略 1: 天天基金
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
        except:
            pass

        # 策略 2: 腾讯基金接口
        try:
            url = f"http://qt.gtimg.cn/q=jj{code}"
            resp = self.session.get(url, timeout=3)
            if resp.status_code == 200 and "v_jj" in resp.text:
                content = resp.text.split('="')[1].strip('";\n')
                parts = content.split('~')
                if len(parts) > 1 and parts[1]:
                    return parts[1]
        except:
            pass

        # 策略 3: Akshare
        try:
            df = ak.fund_individual_basic_info_em(symbol=code)
            for kw in ["基金简称", "基金全称", "基金名称"]:
                row = df[df['item'] == kw]
                if not row.empty:
                    name = row['value'].values[0]
                    if name and str(name).strip():
                        return str(name).strip()
        except:
            pass

        return code

    def get_fund_name(self, code: str) -> str:
        """获取基金名称"""
        return self.fund_names_map.get(code, code)

    def get_realtime_estimates_all(self, console: Console) -> List[Dict]:
        """
        ✅ 增强版：支持多数据源降级策略（静默模式）
        """
        if not self.fund_codes:
            return []

        results = []

        # ✅ 不显示spinner状态，静默执行
        for code in self.fund_codes:
            # 优先级1: 天天基金实时估值
            item = self._try_tiantian_fund(code)

            # 优先级2: LOF场内行情（新浪）
            if item['status'] in ['无数据(解析空)', '非交易时段'] and code.startswith(('16', '50')):
                lof_data = self._try_sina_lof(code)
                if lof_data:
                    item = lof_data

            # 优先级3: AKShare LOF实时行情
            if item['status'] in ['无数据(解析空)', '非交易时段']:
                ak_data = self._try_akshare_lof(code)
                if ak_data:
                    item = ak_data

            # 优先级4: 最新净值降级
            if item['status'] in ['无数据(解析空)', '非交易时段']:
                fallback = self._try_latest_nav(code)
                if fallback:
                    item = fallback

            results.append(item)

        return results

    def _try_tiantian_fund(self, code: str) -> Dict:
        """尝试天天基金接口"""
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

            if resp.status_code == 200 and resp.text:
                text = resp.text.replace("jsonpgz(", "").replace(");", "").strip()

                if text:
                    data = json.loads(text)

                    if 'name' in data and data['name']:
                        self.fund_names_map[code] = data['name']
                        item['name'] = data['name']

                    item['gz'] = data.get('gsz')
                    item['gszzl'] = data.get('gszzl')
                    item['time'] = data.get('gztime', '--')
                    item['status'] = '正常' if item['gz'] else '非交易时段'
                else:
                    item['status'] = '无数据(解析空)'
            else:
                item['status'] = f'HTTP {resp.status_code}'

        except Exception:
            item['status'] = '网络错误'

        return item

    def _try_sina_lof(self, code: str) -> Optional[Dict]:
        """尝试新浪LOF场内行情"""
        try:
            url = f"http://hq.sinajs.cn/list=sz{code}"
            resp = self.session.get(url, timeout=3)

            if 'var hq_str' in resp.text:
                content = resp.text.split('="')[1].strip('";')
                fields = content.split(',')

                if len(fields) > 10 and fields[0]:
                    current_price = float(fields[3])
                    prev_close = float(fields[2])
                    change_pct = ((current_price - prev_close) / prev_close * 100) if prev_close > 0 else 0

                    return {
                        'code': code,
                        'name': fields[0],
                        'gz': current_price,
                        'gszzl': round(change_pct, 2),
                        'time': fields[31] if len(fields) > 31 else '--',
                        'status': '场内行情'
                    }
        except:
            pass
        return None

    def _try_akshare_lof(self, code: str) -> Optional[Dict]:
        """尝试AKShare LOF数据"""
        try:
            # ✅ 禁用akshare内部进度条
            import sys
            from io import StringIO

            old_stdout = sys.stdout
            sys.stdout = StringIO()  # 重定向标准输出

            try:
                df = ak.fund_lof_spot_em()
            finally:
                sys.stdout = old_stdout  # 恢复标准输出

            row = df[df['代码'] == code]

            if not row.empty:
                return {
                    'code': code,
                    'name': str(row['名称'].values[0]),
                    'gz': float(row['最新价'].values[0]),
                    'gszzl': float(row['涨跌幅'].values[0]),
                    'time': '--',
                    'status': 'LOF行情'
                }
        except:
            pass
        return None

    def _try_latest_nav(self, code: str) -> Optional[Dict]:
        """
        ✅ 降级：使用最新净值
        备注：适用于005051等无公开实时估值的港股通基金
        """
        try:
            # ✅ 同样禁用进度条
            import sys
            from io import StringIO

            old_stdout = sys.stdout
            sys.stdout = StringIO()

            try:
                df = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
            finally:
                sys.stdout = old_stdout

            if not df.empty:
                latest = df.iloc[-1]
                return {
                    'code': code,
                    'name': self.get_fund_name(code),
                    'gz': float(latest['单位净值']),
                    'gszzl': None,
                    'time': latest['净值日期'].strftime('%Y-%m-%d'),
                    'status': '最新净值'
                }
        except:
            pass
        return None

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

    def _analyze_trend(self, hist_data: pd.DataFrame, direction: str) -> Tuple[int, float]:
        """分析趋势：返回带符号的涨跌幅"""
        if hist_data.empty:
            return 0, 0.0
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

        if days == 0:
            return 0, 0.0

        total_chg = np.prod([1 + r for r in changes]) - 1

        if direction == 'down':
            total_chg = -abs(total_chg)
        else:
            total_chg = abs(total_chg)

        return days, total_chg

    def screen_funds(self, direction: str, min_days: int, min_pct: float, console: Console) -> List[Dict]:
        """筛选符合条件的基金"""
        results = []
        for code in self.fund_codes:
            hist = self.get_historical_nav(code)
            if hist.empty:
                continue

            days, total_chg = self._analyze_trend(hist, direction)

            if days >= min_days or abs(total_chg) >= min_pct:
                results.append({
                    'code': code,
                    'name': self.get_fund_name(code),
                    'days': days,
                    'pct': round(total_chg * 100, 2)
                })

        return results


# =============================================================================
# 📈 绘图管理类
# =============================================================================
class PlotManager:
    """基金图表管理类"""

    @staticmethod
    def setup_font(console):
        """设置中文字体"""
        try:
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', 'PingFang SC']
            plt.rcParams['axes.unicode_minus'] = False
        except Exception as e:
            console.print(f"[yellow]字体设置警告: {e}[/yellow]")

    @staticmethod
    def get_start_date(range_str: str):
        """根据范围字符串获取起始日期"""
        range_map = {
            '1W': Week(1), '1M': DateOffset(months=1),
            '3M': DateOffset(months=3), '6M': DateOffset(months=6),
            '1Y': DateOffset(years=1)
        }
        return pd.Timestamp.now() - range_map.get(range_str, DateOffset(months=3))

    @staticmethod
    def fetch_benchmark(symbol: str, start_date):
        """获取基准指数数据"""
        try:
            df = ak.stock_zh_index_daily(symbol=symbol)
            df['date'] = pd.to_datetime(df['date'])
            df = df[df['date'] >= start_date].sort_values('date')
            return df
        except:
            return pd.DataFrame()

    @staticmethod
    def plot(tracker, mode: int, range_str: str, show_bench: bool, console: Console):
        """绘制基金图表"""
        if mode == 0:
            return

        console.print(f"\n[bold]📈 正在生成图表 (模式: {mode}, 范围: {range_str})...[/bold]")
        PlotManager.setup_font(console)
        start_date = PlotManager.get_start_date(range_str)

        fund_data = {}
        for code in tracker.fund_codes:
            df = tracker.get_historical_nav(code)
            if not df.empty:
                df = df[df['净值日期'] >= start_date]
                if not df.empty:
                    fund_data[code] = df

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

            if count == 1:
                axes = [axes]
            else:
                axes = axes.flatten()

            for i, (code, df) in enumerate(fund_data.items()):
                ax = axes[i]
                name = tracker.get_fund_name(code)
                ax.plot(df['净值日期'], df['累计净值'], color='#1f77b4', lw=2)
                ax.set_title(f"{name}\n({code})", fontsize=11, pad=10)
                ax.grid(True, ls=':', alpha=0.6)
                ax.tick_params(axis='x', rotation=30, labelsize=9)

            if count > 1:
                for j in range(i + 1, len(axes)):
                    axes[j].axis('off')
            plt.show()


# =============================================================================
# 🖥️ 界面渲染函数
# =============================================================================
def print_realtime_table(console: Console, data_list: List[Dict]) -> None:
    """打印实时估值表格"""
    # ✅ 修复：标题左对齐
    table = Table(
        title="\n📈 基金实时估值",
        title_justify="left",  # ✅ 左对齐
        show_header=True,
        header_style="bold magenta",
        border_style="dim"
    )

    table.add_column("基金代码", justify="left", style="cyan")
    table.add_column("基金名称", justify="left", style="white")
    table.add_column("估算净值", justify="right")
    table.add_column("估算涨跌幅", justify="right")
    table.add_column("估值时间", justify="center", style="dim")
    table.add_column("状态/备注", justify="left")

    for item in data_list:
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
    """打印筛选结果表格"""
    if df.empty:
        console.print(f"\n  [italic dim]（{title} 无数据）[/italic dim]")
        return

    # ✅ 修复：标题左对齐
    table = Table(
        title=title,
        title_justify="left",  # ✅ 左对齐
        show_header=True,
        header_style="bold magenta",
        border_style="dim",
        show_lines=False
    )

    table.add_column("基金代码", justify="left", style="cyan")
    table.add_column("基金名称", justify="left")
    table.add_column("连续天数", justify="right")
    table.add_column("累计涨跌幅(%)", justify="right")

    for _, row in df.iterrows():
        pct = row['pct']

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


def load_fund_codes(config: dict) -> List[str]:
    """加载基金代码列表"""
    codes = []
    if os.path.exists(config["file_path"]):
        with open(config["file_path"], 'r', encoding='utf-8') as f:
            codes = [l.strip() for l in f if l.strip()]
    else:
        codes = config["default_funds"]
    return codes


def update_config_from_args(config: dict, args: argparse.Namespace) -> dict:
    """根据命令行参数更新配置"""
    config["screen_up"]["days"] = args.up_days
    config["screen_up"]["pct"] = args.up_pct
    config["screen_down"]["days"] = args.down_days
    config["screen_down"]["pct"] = args.down_pct
    config["plot_mode"] = args.plot_mode
    config["plot_range"] = args.plot_range
    return config
