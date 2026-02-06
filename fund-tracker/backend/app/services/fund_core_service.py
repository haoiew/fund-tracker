# -*- coding: utf-8 -*-
"""
基金核心服务 - 统一管理基金数据（首页、基金筛、基金对、持仓管理）
集成 fund_main.py 的所有功能，实现数据互通
"""
import asyncio
import json
import time
import os
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import List, Dict, Optional, Any, Set, Tuple
from pathlib import Path

import requests
import akshare as ak
import pandas as pd
import numpy as np
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.config import fund_config, chart_config
from app.models.fund import FundNavHistory
from app.schemas.fund import FundRealtimeData, FundTrendScreenResult, FundChartData
from app.services.cache_service import get_cache_service
from app.services.history_service import history_service
from app.services.fund_data_source import get_data_source_manager, DataSourceType
from app.logger import get_logger

logger = get_logger("fund_core_service")

os.environ['TQDM_DISABLE'] = '1'
warnings_filtered = False


def _setup_warnings():
    global warnings_filtered
    if not warnings_filtered:
        import warnings
        warnings.filterwarnings("ignore")
        warnings_filtered = True


class FundCoreService:
    """
    基金核心服务单例
    
    统一管理：
    - 基金列表（funds.txt）
    - 实时数据（多级降级策略）
    - 历史净值（本地持久化 + 后台异步更新）
    - 基准指数（支持对比功能）
    - 基金筛选（连续涨跌分析）
    """
    
    _instance: Optional['FundCoreService'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self.cache = get_cache_service()
        self._update_locks: Dict[str, asyncio.Lock] = {}
        
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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        self._fund_names_cache: Dict[str, str] = {}
        self._init_fund_list()
    
    def _init_fund_list(self):
        """初始化基金列表"""
        self._fund_list: List[str] = []
        self._fund_list_path = fund_config.FUND_FILE_PATH
        
        if os.path.exists(self._fund_list_path):
            with open(self._fund_list_path, 'r', encoding='utf-8') as f:
                self._fund_list = [line.strip() for line in f if line.strip()]
        else:
            self._fund_list = fund_config.DEFAULT_FUNDS.copy()
            self.save_fund_list()
        
        logger.info(f"✅ 基金列表已加载: {len(self._fund_list)} 只")
    
    def save_fund_list(self):
        """保存基金列表"""
        try:
            with open(self._fund_list_path, 'w', encoding='utf-8') as f:
                for code in self._fund_list:
                    f.write(f"{code}\n")
            logger.info(f"💾 基金列表已保存: {self._fund_list_path}")
        except Exception as e:
            logger.error(f"保存基金列表失败: {e}")
    
    def get_fund_list(self) -> List[str]:
        """获取基金列表"""
        return self._fund_list.copy()
    
    def add_fund(self, code: str) -> bool:
        """添加基金"""
        code = str(code).strip()
        if code not in self._fund_list:
            self._fund_list.append(code)
            self.save_fund_list()
            logger.info(f"➕ 添加基金: {code}")
            return True
        return False
    
    def remove_fund(self, code: str) -> bool:
        """移除基金"""
        code = str(code).strip()
        if code in self._fund_list:
            self._fund_list.remove(code)
            self.save_fund_list()
            logger.info(f"➖ 移除基金: {code}")
            return True
        return False
    
    def get_fund_name(self, code: str) -> str:
        """获取基金名称（三级降级策略）"""
        if code in self._fund_names_cache:
            return self._fund_names_cache[code]
        
        name = self._fetch_fund_name(code)
        self._fund_names_cache[code] = name
        return name
    
    def _fetch_fund_name(self, code: str) -> str:
        """获取基金名称"""
        _setup_warnings()
        
        for strategy in [self._name_from_tiantian, self._name_from_tencent, self._name_from_akshare]:
            try:
                name = strategy(code)
                if name and name != code:
                    return name
            except Exception as e:
                logger.debug(f"获取名称策略失败 {code}: {e}")
        return code
    
    def _name_from_tiantian(self, code: str) -> str:
        """天天基金获取名称"""
        ts = int(time.time() * 1000)
        url = f"http://fundgz.1234567.com.cn/js/{code}.js?rt={ts}"
        resp = self.session.get(url, timeout=3)
        if resp.status_code == 200 and resp.text:
            text = resp.text.strip().replace("jsonpgz(", "").replace(");", "")
            if text:
                data = json.loads(text)
                if 'name' in data and data['name']:
                    return data['name']
        return None
    
    def _name_from_tencent(self, code: str) -> str:
        """腾讯基金获取名称"""
        url = f"http://qt.gtimg.cn/q=jj{code}"
        resp = self.session.get(url, timeout=3)
        if resp.status_code == 200 and "v_jj" in resp.text:
            content = resp.text.split('="')[1].strip('";\n')
            parts = content.split('~')
            if len(parts) > 1 and parts[1]:
                return parts[1]
        return None
    
    def _name_from_akshare(self, code: str) -> str:
        """AKShare获取名称"""
        _setup_warnings()
        df = ak.fund_individual_basic_info_em(symbol=code)
        for kw in ["基金简称", "基金全称", "基金名称"]:
            row = df[df['item'] == kw]
            if not row.empty:
                name = row['value'].values[0]
                if name and str(name).strip():
                    return str(name).strip()
        return None
    
    async def get_realtime_data_async(self, code: str) -> FundRealtimeData:
        """异步获取实时估值（多数据源并发加载）"""
        cache_key = f"realtime:{code}"
        cached = self.cache.get(cache_key)
        if cached:
            if isinstance(cached, dict):
                try:
                    return FundRealtimeData(**cached)
                except:
                    pass
            elif isinstance(cached, FundRealtimeData):
                return cached
        
        name = self.get_fund_name(code)
        
        # 使用数据源管理器并发获取所有数据源
        ds_manager = get_data_source_manager()
        results = await ds_manager.fetch_all_sources(code, name)
        
        # 选择最佳数据源
        best, alternatives = ds_manager.select_best_data(results)
        
        if best:
            data = best.data
            result = FundRealtimeData(
                code=code,
                name=data.get('name', name),
                estimate_nav=Decimal(str(data['gz'])) if data.get('gz') else None,
                estimate_change=Decimal(str(data['gszzl'])) if data.get('gszzl') else None,
                previous_nav=Decimal(str(data.get('dwjz'))) if data.get('dwjz') else None,
                update_time=data.get('time', '--'),
                status=data.get('status', '未知'),
                data_source=best.source_type.value,
                data_timestamp=best.timestamp.isoformat() if best.timestamp else None
            )
        else:
            # 所有数据源都失败
            result = FundRealtimeData(
                code=code,
                name=name,
                status='获取失败'
            )
        
        self.cache.set(cache_key, result, 60)
        return result
    
    def get_realtime_data(self, code: str) -> FundRealtimeData:
        """获取实时估值（同步包装）"""
        try:
            # 尝试获取事件循环
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果事件循环正在运行，创建新任务
                return asyncio.run_coroutine_threadsafe(
                    self.get_realtime_data_async(code), loop
                ).result(timeout=10)
            else:
                return loop.run_until_complete(self.get_realtime_data_async(code))
        except RuntimeError:
            # 没有事件循环，创建新的
            return asyncio.run(self.get_realtime_data_async(code))
        except Exception as e:
            logger.error(f"获取实时数据失败 {code}: {e}")
            return FundRealtimeData(
                code=code,
                name=self.get_fund_name(code),
                status='获取失败'
            )
    
    def get_realtime_batch(self, codes: List[str]) -> List[FundRealtimeData]:
        """批量获取实时数据（同步包装）"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return asyncio.run_coroutine_threadsafe(
                    self.get_realtime_batch_async(codes), loop
                ).result(timeout=30)
            else:
                return loop.run_until_complete(self.get_realtime_batch_async(codes))
        except RuntimeError:
            return asyncio.run(self.get_realtime_batch_async(codes))
        except Exception as e:
            logger.error(f"批量获取实时数据失败: {e}")
            # 降级为逐个获取
            results = []
            for code in codes:
                try:
                    data = self.get_realtime_data(code)
                    results.append(data)
                except Exception as e2:
                    logger.error(f"获取实时数据失败 {code}: {e2}")
                    results.append(FundRealtimeData(
                        code=code,
                        name=self.get_fund_name(code),
                        status='获取失败'
                    ))
            return results

    async def get_realtime_batch_async(self, codes: List[str]) -> List[FundRealtimeData]:
        """
        批量获取实时数据（真正并发）
        使用 asyncio.gather 同时获取所有基金数据，大幅提升性能
        """
        if not codes:
            return []

        logger.info(f"开始并发获取 {len(codes)} 只基金的实时数据")
        start_time = time.time()

        # 创建并发任务
        tasks = [self.get_realtime_data_async(code) for code in codes]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_results = []
        for code, result in zip(codes, results):
            if isinstance(result, Exception):
                logger.error(f"获取实时数据失败 {code}: {result}")
                valid_results.append(FundRealtimeData(
                    code=code,
                    name=self.get_fund_name(code),
                    status='获取失败'
                ))
            else:
                valid_results.append(result)

        elapsed = time.time() - start_time
        logger.info(f"并发获取完成: {len(codes)} 只基金, 耗时 {elapsed:.2f}s")

        return valid_results
    
    def _try_tiantian_fund(self, code: str, name: str) -> Dict:
        """天天基金实时估值"""
        item = {
            'code': code, 'name': name, 'gz': None, 'gszzl': None,
            'dwjz': None, 'time': '--', 'status': '获取中'
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
                        item['name'] = data['name']
                        self._fund_names_cache[code] = data['name']
                    item['gz'] = data.get('gsz')
                    item['gszzl'] = data.get('gszzl')
                    item['dwjz'] = data.get('dwjz')  # 昨日净值/单位净值
                    item['time'] = data.get('gztime', '--')
                    item['status'] = '正常' if item['gz'] else '非交易时段'
        except Exception as e:
            logger.debug(f"天天基金接口失败 {code}: {e}")
            item['status'] = '网络错误'
        return item
    
    def _try_sina_lof(self, code: str) -> Optional[Dict]:
        """新浪LOF场内行情"""
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
                        'code': code, 'name': fields[0],
                        'gz': current_price, 'gszzl': round(change_pct, 2),
                        'time': fields[31] if len(fields) > 31 else '--',
                        'status': '场内行情'
                    }
        except Exception as e:
            logger.debug(f"新浪LOF接口失败 {code}: {e}")
        return None
    
    def _try_akshare_lof(self, code: str) -> Optional[Dict]:
        """AKShare LOF数据"""
        try:
            _setup_warnings()
            df = ak.fund_lof_spot_em()
            row = df[df['代码'] == code]
            if not row.empty:
                return {
                    'code': code, 'name': str(row['名称'].values[0]),
                    'gz': float(row['最新价'].values[0]),
                    'gszzl': float(row['涨跌幅'].values[0]),
                    'time': '--', 'status': 'LOF行情'
                }
        except Exception as e:
            logger.debug(f"AKShare LOF接口失败 {code}: {e}")
        return None
    
    def _try_latest_nav(self, code: str, name: str) -> Optional[Dict]:
        """最新净值降级"""
        try:
            _setup_warnings()
            df = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
            if not df.empty:
                latest = df.iloc[-1]
                return {
                    'code': code, 'name': name,
                    'gz': float(latest['单位净值']),
                    'gszzl': None,
                    'time': latest['净值日期'].strftime('%Y-%m-%d'),
                    'status': '最新净值'
                }
        except Exception as e:
            logger.debug(f"获取最新净值失败 {code}: {e}")
        return None
    
    async def get_chart_data(
        self, 
        code: str, 
        range_str: str = "3M",
        use_local_first: bool = True
    ) -> Dict[str, Any]:
        """
        获取图表数据
        
        策略：
        1. 先返回本地数据库缓存（快速响应）
        2. 后台异步检查并更新缺失数据
        """
        days = chart_config.TIME_RANGES.get(range_str, {}).get('days', 90)
        
        if use_local_first:
            result = await history_service.get_chart_data_with_fallback(code, range_str)
            return result
        else:
            fresh_data = await history_service._fetch_and_store(code, days)
            return {'data': fresh_data, 'source': 'fresh', 'updating': False}
    
    def get_benchmark_data(self, symbol: str, days: int = 365) -> Dict:
        """获取基准指数数据"""
        cache_key = f"benchmark:{symbol}:{days}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        _setup_warnings()
        try:
            df = ak.stock_zh_index_daily(symbol=symbol)
            df['date'] = pd.to_datetime(df['date'])
            
            if days > 0:
                start_date = datetime.now() - timedelta(days=days)
                df = df[df['date'] >= start_date]
            
            df = df.sort_values('date')
            
            if df.empty:
                result = {"dates": [], "values": [], "changes": []}
            else:
                start_value = df['close'].iloc[0]
                df['pct_change'] = ((df['close'] - start_value) / start_value * 100).round(2)
                
                result = {
                    "symbol": symbol,
                    "dates": df['date'].dt.strftime('%Y-%m-%d').tolist(),
                    "values": [float(v) for v in df['close'].tolist()],
                    "changes": [float(v) for v in df['pct_change'].tolist()],
                    "start_value": float(start_value)
                }
            
            self.cache.set(cache_key, result, 3600)
            return result
        except Exception as e:
            logger.error(f"获取基准指数失败 {symbol}: {e}")
            return {"dates": [], "values": [], "changes": []}
    
    def get_compare_data(
        self,
        codes: List[str],
        range_str: str = "1M",
        include_benchmark: bool = True,
        batch_size: int = 3,
        delay_between_batches: float = 1.0
    ) -> Dict[str, Any]:
        """
        获取对比数据（带批量控制和延迟）

        返回：
        - funds: 各基金的图表数据
        - benchmarks: 基准指数数据（可选）
        """
        result = {"funds": [], "benchmarks": [], "range": range_str}
        total_codes = len(codes)
        processed = 0
        failed = 0

        logger.info(f"开始获取对比数据: {total_codes} 只基金, 范围: {range_str}")

        # 分批处理基金代码
        for i in range(0, total_codes, batch_size):
            batch = codes[i:i + batch_size]

            for code in batch:
                try:
                    data = self.get_benchmark_nav_data(code, range_str)
                    result["funds"].append({
                        "code": code,
                        "name": self.get_fund_name(code),
                        **data
                    })
                    processed += 1
                except Exception as e:
                    failed += 1
                    logger.warning(f"获取对比数据失败 {code}: {e}")
                    # 添加空数据占位
                    result["funds"].append({
                        "code": code,
                        "name": self.get_fund_name(code),
                        "dates": [],
                        "changes": []
                    })

            # 批次间延迟
            if i + batch_size < total_codes:
                time.sleep(delay_between_batches)

        if include_benchmark:
            benchmarks = [
                {"name": "上证指数", "symbol": "sh000001"},
                {"name": "沪深300", "symbol": "sh000300"}
            ]
            for bench in benchmarks:
                try:
                    bench_data = self.get_benchmark_data(bench["symbol"],
                        chart_config.TIME_RANGES.get(range_str, {}).get('days', 30))
                    result["benchmarks"].append({
                        **bench,
                        **bench_data
                    })
                except Exception as e:
                    logger.warning(f"获取基准数据失败 {bench['symbol']}: {e}")

        logger.info(f"对比数据获取完成: 成功 {processed} 只, 失败 {failed} 只")
        return result
    
    def get_benchmark_nav_data(self, code: str, range_str: str) -> Dict[str, List]:
        """获取基金的净值数据用于对比"""
        days = chart_config.TIME_RANGES.get(range_str, {}).get('days', 90)
        
        df = self.get_historical_nav(code, days)
        if df.empty:
            return {"dates": [], "changes": []}
        
        start_value = df['累计净值'].iloc[0]
        df['pct_change'] = ((df['累计净值'] - start_value) / start_value * 100).round(2)
        
        return {
            "dates": df['净值日期'].dt.strftime('%Y-%m-%d').tolist(),
            "changes": [float(v) if pd.notna(v) else None for v in df['pct_change'].tolist()]
        }
    
    def get_historical_nav(self, code: str, days: int = 365, max_retries: int = 3) -> pd.DataFrame:
        """获取历史净值（AKShare为主，东方财富为备份）"""
        _setup_warnings()

        # 检查缓存
        cache_key = f"nav_history:{code}:{days}"
        cached = self.cache.get(cache_key)
        if cached and isinstance(cached, pd.DataFrame) and not cached.empty:
            logger.debug(f"使用缓存的历史净值数据: {code}")
            return cached

        # 策略1: 使用AKShare获取（主数据源）
        df = self._get_historical_nav_from_akshare(code, days, max_retries)
        if not df.empty:
            return df

        # 策略2: 使用东方财富直接接口（备份数据源）
        logger.warning(f"AKShare获取失败，尝试东方财富备份接口: {code}")
        df = self._get_historical_nav_from_eastmoney(code, days, max_retries)
        if not df.empty:
            return df

        logger.error(f"所有数据源获取历史净值失败: {code}")
        return pd.DataFrame()

    def _get_historical_nav_from_akshare(self, code: str, days: int, max_retries: int) -> pd.DataFrame:
        """从AKShare获取历史净值"""
        for attempt in range(max_retries):
            try:
                # 禁用akshare内部进度条
                import sys
                from io import StringIO
                old_stdout = sys.stdout
                sys.stdout = StringIO()

                try:
                    df = ak.fund_open_fund_info_em(symbol=code, indicator="累计净值走势")
                finally:
                    sys.stdout = old_stdout

                if df is None or df.empty:
                    if attempt < max_retries - 1:
                        wait_time = 0.5 * (2 ** attempt)
                        logger.warning(f"AKShare获取历史净值为空，{wait_time}s后重试 ({attempt + 1}/{max_retries}): {code}")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.warning(f"AKShare获取历史净值失败: {code}")
                        return pd.DataFrame()

                df['净值日期'] = pd.to_datetime(df['净值日期'])
                df['累计净值'] = pd.to_numeric(df['累计净值'])
                df = df.sort_values('净值日期').reset_index(drop=True)
                df['pct_change'] = df['累计净值'].pct_change().fillna(0)

                if days > 0:
                    start_date = datetime.now() - timedelta(days=days)
                    df = df[df['净值日期'] >= start_date]

                # 缓存结果（5分钟）
                cache_key = f"nav_history:{code}:{days}"
                self.cache.set(cache_key, df, 300)
                logger.info(f"✅ AKShare获取历史净值成功: {code}, {len(df)}条")
                return df

            except Exception as e:
                error_msg = str(e)
                if 'SSL' in error_msg or 'EOF' in error_msg:
                    logger.warning(f"AKShare SSL错误，{2 ** attempt}s后重试 ({attempt + 1}/{max_retries}): {code}")
                else:
                    logger.warning(f"AKShare获取失败，{2 ** attempt}s后重试 ({attempt + 1}/{max_retries}): {code} - {error_msg[:80]}")

                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)

        return pd.DataFrame()

    def _get_historical_nav_from_eastmoney(self, code: str, days: int, max_retries: int) -> pd.DataFrame:
        """从东方财富直接接口获取历史净值（备份）"""
        for attempt in range(max_retries):
            try:
                url = f"http://fund.eastmoney.com/pingzhongdata/{code}.js"
                resp = self.session.get(url, timeout=10)

                if resp.status_code != 200:
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    return pd.DataFrame()

                # 解析JavaScript数据
                text = resp.text

                # 提取Data_netWorthTrend（单位净值）
                import re
                match = re.search(r'Data_netWorthTrend\s*=\s*(\[.*?\]);', text, re.DOTALL)
                if not match:
                    logger.warning(f"东方财富数据解析失败: {code}")
                    return pd.DataFrame()

                data = json.loads(match.group(1))

                if not data:
                    return pd.DataFrame()

                # 转换为DataFrame
                df = pd.DataFrame(data)
                df['x'] = pd.to_datetime(df['x'], unit='ms')
                df['y'] = pd.to_numeric(df['y'])
                df = df.rename(columns={'x': '净值日期', 'y': '累计净值'})
                df = df.sort_values('净值日期').reset_index(drop=True)
                df['pct_change'] = df['累计净值'].pct_change().fillna(0)

                if days > 0:
                    start_date = datetime.now() - timedelta(days=days)
                    df = df[df['净值日期'] >= start_date]

                # 缓存结果（5分钟）
                cache_key = f"nav_history:{code}:{days}"
                self.cache.set(cache_key, df, 300)
                logger.info(f"✅ 东方财富备份接口获取成功: {code}, {len(df)}条")
                return df

            except Exception as e:
                error_msg = str(e)
                if 'SSL' in error_msg or 'EOF' in error_msg:
                    logger.warning(f"东方财富SSL错误，{2 ** attempt}s后重试: {code}")
                else:
                    logger.debug(f"东方财富获取失败: {code} - {error_msg[:80]}")

                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)

        return pd.DataFrame()
    
    def analyze_trend(self, hist_data: pd.DataFrame, direction: str) -> Tuple[int, float]:
        """分析趋势：返回(连续天数, 累计涨跌幅)"""
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
    
    def screen_funds(
        self,
        codes: Optional[List[str]] = None,
        direction: str = 'up',
        min_days: int = 2,
        min_pct: float = 0.03,
        batch_size: int = 3,
        delay_between_batches: float = 1.0
    ) -> List[Dict]:
        """
        筛选基金（带批量控制和延迟）

        Args:
            codes: 基金列表，None 则使用全部基金
            direction: up(连续上涨) / down(连续下跌)
            min_days: 最少连续天数
            min_pct: 最少累计涨跌幅
            batch_size: 每批处理的基金数量（避免并发过高）
            delay_between_batches: 批次之间的延迟（秒）

        Returns:
            满足条件的基金列表
        """
        if codes is None:
            codes = self._fund_list

        results = []
        total_codes = len(codes)
        processed = 0
        failed = 0

        logger.info(f"开始筛选基金: {total_codes} 只, 方向: {direction}, 最小天数: {min_days}, 最小幅度: {min_pct}%")

        for i in range(0, total_codes, batch_size):
            batch = codes[i:i + batch_size]

            for code in batch:
                try:
                    hist = self.get_historical_nav(code, 365)
                    if hist.empty:
                        failed += 1
                        continue

                    days, total_chg = self.analyze_trend(hist, direction)

                    if days >= min_days or abs(total_chg) >= min_pct:
                        results.append({
                            'code': code,
                            'name': self.get_fund_name(code),
                            'days': days,
                            'pct': round(total_chg * 100, 2)
                        })

                    processed += 1

                except Exception as e:
                    failed += 1
                    logger.debug(f"筛选基金失败 {code}: {e}")

            # 批次间延迟，避免请求过快
            if i + batch_size < total_codes:
                time.sleep(delay_between_batches)

        logger.info(f"筛选完成: 处理 {processed} 只, 失败 {failed} 只, 符合条件 {len(results)} 只")

        return sorted(results, key=lambda x: abs(x['pct']), reverse=True)
    
    def get_screen_result(
        self,
        direction: str = 'up',
        min_days: Optional[int] = None,
        min_pct: Optional[float] = None
    ) -> Dict[str, Any]:
        """获取筛选结果（带缓存）"""
        min_days = min_days if min_days is not None else fund_config.SCREEN_UP["days"] if direction == 'up' else fund_config.SCREEN_DOWN["days"]
        min_pct = min_pct if min_pct is not None else fund_config.SCREEN_UP["pct"] if direction == 'up' else fund_config.SCREEN_DOWN["pct"]
        
        cache_key = f"screen:{direction}:{min_days}:{min_pct}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        results = self.screen_funds(direction=direction, min_days=min_days, min_pct=min_pct)
        
        result = {
            'direction': direction,
            'min_days': min_days,
            'min_pct': min_pct,
            'count': len(results),
            'funds': results
        }
        
        self.cache.set(cache_key, result, 300)
        return result
    
    async def preload_data(self, codes: List[str], priority: str = 'normal'):
        """预加载基金数据"""
        delay = 0
        if priority == 'high':
            delay = 0
        elif priority == 'normal':
            delay = 2
        else:
            delay = 5
        
        if delay > 0:
            await asyncio.sleep(delay)
        
        for code in codes:
            try:
                self.get_realtime_data(code)
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"预加载失败 {code}: {e}")
    
    async def preload_fund_history(self, codes: List[str], priority: str = 'normal'):
        """
        预加载基金历史数据到本地缓存
        
        Args:
            codes: 基金代码列表
            priority: 优先级 ('high', 'normal', 'low')
        """
        if not codes:
            return

        # 去重
        unique_codes = list(set(codes))
        logger.info(f"🔄 预加载基金历史数据: {len(unique_codes)} 只")

        # 根据优先级设置延迟
        delay = {'high': 0, 'normal': 1, 'low': 3}.get(priority, 1)
        if delay > 0:
            await asyncio.sleep(delay)

        # 批量预加载
        for code in unique_codes:
            try:
                # 使用增量更新（会自动判断是否需要全量）
                result = await history_service.incremental_update(code)
                if result.get('full_update'):
                    logger.info(f"✅ 全量缓存完成: {code}, {result.get('records', 0)} 条")
                elif result.get('updated', 0) > 0:
                    logger.info(f"✅ 增量更新完成: {code}, +{result.get('updated')} 条")
                else:
                    logger.debug(f"⏭️ 数据已最新: {code}")

                # 小延迟避免并发过高
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.warning(f"预加载失败 {code}: {e}")

    def get_portfolio_with_realtime(
        self,
        portfolio_items: List[Dict]
    ) -> List[Dict]:
        """
        持仓数据关联实时数据

        Args:
            portfolio_items: [{'fund_code': '016531', 'shares': 100, ...}, ...]

        Returns:
            合并了实时数据的持仓列表
        """
        result = []

        for item in portfolio_items:
            code = str(item.get('fund_code', ''))
            realtime = self.get_realtime_data(code)
            
            merged = {
                **item,
                'fund_name': realtime.name,
                'estimate_nav': realtime.estimate_nav,
                'estimate_change': realtime.estimate_change,
                'update_time': realtime.update_time,
                'data_source': realtime.data_source,
                'status': realtime.status
            }
            
            if realtime.estimate_nav and item.get('cost_price'):
                try:
                    profit = (realtime.estimate_nav - Decimal(str(item['cost_price']))) * Decimal(str(item.get('shares', 0)))
                    merged['profit_loss'] = profit
                except:
                    pass
            
            result.append(merged)
        
        return result
    
    def search_funds(self, keyword: str, limit: int = 10) -> List[Dict]:
        """搜索基金（AKShare为主，东方财富为备份）"""
        _setup_warnings()

        # 策略1: 使用AKShare搜索
        results = self._search_funds_from_akshare(keyword, limit)
        if results:
            return results

        # 策略2: 使用东方财富备份搜索
        logger.warning(f"AKShare搜索失败，尝试东方财富备份: {keyword}")
        results = self._search_funds_from_eastmoney(keyword, limit)
        if results:
            return results

        return []

    def _search_funds_from_akshare(self, keyword: str, limit: int) -> List[Dict]:
        """从AKShare搜索基金"""
        results = []
        max_retries = 3

        for attempt in range(max_retries):
            try:
                # 禁用akshare内部进度条
                import sys
                from io import StringIO
                old_stdout = sys.stdout
                sys.stdout = StringIO()

                try:
                    df = ak.fund_name_em()
                finally:
                    sys.stdout = old_stdout

                if df is None or df.empty:
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    return []

                # 模糊匹配基金名称和代码
                mask = df['基金简称'].str.contains(keyword, na=False, case=False) | \
                       df['基金代码'].str.contains(keyword, na=False)
                matched = df[mask].head(limit)

                for _, row in matched.iterrows():
                    results.append({
                        'code': str(row['基金代码']),
                        'name': str(row['基金简称']),
                        'type': str(row.get('基金类型', '')),
                        'company': str(row.get('基金公司', ''))
                    })

                if results:
                    logger.info(f"✅ AKShare搜索成功: {keyword}, 找到 {len(results)} 条")
                return results

            except Exception as e:
                error_msg = str(e)
                if 'SSL' in error_msg or 'EOF' in error_msg:
                    logger.warning(f"AKShare搜索SSL错误，{2 ** attempt}s后重试: {keyword}")
                else:
                    logger.warning(f"AKShare搜索失败，{2 ** attempt}s后重试: {keyword} - {error_msg[:80]}")

                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)

        return []

    def _search_funds_from_eastmoney(self, keyword: str, limit: int) -> List[Dict]:
        """从东方财富搜索基金（备份）"""
        results = []
        max_retries = 3

        for attempt in range(max_retries):
            try:
                # 东方财富基金搜索接口
                url = "http://fund.eastmoney.com/js/fundcode_search.js"
                resp = self.session.get(url, timeout=10)

                if resp.status_code != 200:
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    return []

                # 解析JavaScript数据
                text = resp.text
                match = re.search(r'var\s+r\s*=\s*(\[.*?\]);', text, re.DOTALL)
                if not match:
                    return []

                data = json.loads(match.group(1))

                # 模糊匹配
                keyword_lower = keyword.lower()
                matched = []
                for item in data:
                    code = item[0]  # 基金代码
                    name = item[2]  # 基金名称
                    if keyword_lower in code.lower() or keyword_lower in name.lower():
                        matched.append({
                            'code': code,
                            'name': name,
                            'type': item[3] if len(item) > 3 else '',
                            'company': ''
                        })
                    if len(matched) >= limit:
                        break

                if matched:
                    logger.info(f"✅ 东方财富备份搜索成功: {keyword}, 找到 {len(matched)} 条")
                return matched

            except Exception as e:
                error_msg = str(e)
                if 'SSL' in error_msg or 'EOF' in error_msg:
                    logger.warning(f"东方财富搜索SSL错误，{2 ** attempt}s后重试: {keyword}")
                else:
                    logger.debug(f"东方财富搜索失败: {keyword} - {error_msg[:80]}")

                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)

        return []
    
    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            'fund_count': len(self._fund_list),
            'names_cache_size': len(self._fund_names_cache),
            'cache_stats': self.cache.get_stats() if self.cache else None
        }


fund_core_service = FundCoreService()


def get_fund_core_service() -> FundCoreService:
    """获取基金核心服务实例"""
    return fund_core_service
