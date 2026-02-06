# -*- coding: utf-8 -*-
"""
基金数据服务 - 核心业务逻辑
"""
import json
import time
import re
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Any
import requests
import akshare as ak
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.config import fund_config, chart_config
from app.models.fund import Fund, FundNavHistory, FundRealtimeCache
from app.schemas.fund import FundRealtimeData, FundTrendScreenResult, FundChartData
from app.services.cache_service import get_cache_service
from app.logger import get_logger

logger = get_logger("fund_service")

class FundDataService:
    """基金数据服务类"""
    
    def __init__(self):
        self.session = requests.Session()
        retries = Retry(
            total=fund_config.REQUEST_RETRY_TIMES,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        self.session.mount('http://', HTTPAdapter(max_retries=retries))
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0'
        })
        
        # 禁用akshare进度条
        import os
        os.environ['TQDM_DISABLE'] = '1'
        
        # 初始化缓存服务
        self.cache = get_cache_service()
        
        # 错误统计
        self.error_stats = {
            'tiantian': {'success': 0, 'failure': 0},
            'sina_lof': {'success': 0, 'failure': 0},
            'akshare_lof': {'success': 0, 'failure': 0},
            'latest_nav': {'success': 0, 'failure': 0}
        }
    
    def get_fund_name(self, code: str) -> str:
        """获取基金名称（三级降级策略）"""
        from app.logger import get_logger
        logger = get_logger("fund_service")
        
        # 策略1: 天天基金
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
        except Exception as e:
            logger.debug(f"天天基金获取名称失败 {code}: {e}")
        
        # 策略2: 腾讯基金
        try:
            url = f"http://qt.gtimg.cn/q=jj{code}"
            resp = self.session.get(url, timeout=3)
            if resp.status_code == 200 and "v_jj" in resp.text:
                content = resp.text.split('="')[1].strip('";\n')
                parts = content.split('~')
                if len(parts) > 1 and parts[1]:
                    return parts[1]
        except Exception as e:
            logger.debug(f"腾讯基金获取名称失败 {code}: {e}")
        
        # 策略3: AKShare
        try:
            df = ak.fund_individual_basic_info_em(symbol=code)
            for kw in ["基金简称", "基金全称", "基金名称"]:
                row = df[df['item'] == kw]
                if not row.empty:
                    name = row['value'].values[0]
                    if name and str(name).strip():
                        return str(name).strip()
        except Exception as e:
            logger.debug(f"AKShare获取名称失败 {code}: {e}")
        
        return code
    
    def get_realtime_data(self, code: str) -> FundRealtimeData:
        """获取实时估值数据（带缓存）"""
        # 检查缓存
        cache_key = f"realtime:{code}"
        cached = self.cache.get(cache_key)
        
        if cached:
            logger.info(f"✅ 使用缓存数据: {code}")
            # 将字典转换回Pydantic模型
            if isinstance(cached, dict):
                try:
                    return FundRealtimeData(**cached)
                except Exception as e:
                    logger.warning(f"缓存数据转换失败 {code}: {e}")
                    # 缓存数据损坏，删除缓存
                    self.cache.delete(cache_key)
            else:
                return cached
        
        # 缓存未命中，获取数据
        name = self.get_fund_name(code)
        
        # 优先级1: 天天基金
        result = self._try_tiantian_fund(code, name)
        
        # 优先级2: LOF场内行情
        if result.status in ['无数据(解析空)', '非交易时段'] and code.startswith(('16', '50')):
            lof_data = self._try_sina_lof(code)
            if lof_data:
                result = lof_data
        
        # 优先级3: AKShare LOF
        if result.status in ['无数据(解析空)', '非交易时段']:
            ak_data = self._try_akshare_lof(code)
            if ak_data:
                result = ak_data
        
        # 优先级4: 最新净值
        if result.status in ['无数据(解析空)', '非交易时段']:
            fallback = self._try_latest_nav(code, name)
            if fallback:
                result = fallback
        
        # 写入缓存
        self.cache.set(cache_key, result, 60)  # 60 秒 TTL
        
        return result
    
    def _try_tiantian_fund(self, code: str, name: str) -> FundRealtimeData:
        """尝试天天基金接口（带错误统计）"""
        result = FundRealtimeData(code=code, name=name, status="获取中")

        try:
            ts = int(time.time() * 1000)
            url = f"http://fundgz.1234567.com.cn/js/{code}.js?rt={ts}"
            resp = self.session.get(url, timeout=5)

            if resp.status_code == 200 and resp.text:
                text = resp.text.replace("jsonpgz(", "").replace(");", "").strip()

                if text:
                    data = json.loads(text)

                    if 'name' in data and data['name']:
                        result.name = data['name']

                    # 估算净值和涨跌幅
                    result.estimate_nav = Decimal(str(data.get('gsz'))) if data.get('gsz') else None
                    result.estimate_change = Decimal(str(data.get('gszzl'))) if data.get('gszzl') else None

                    # 昨日净值 (dwjz)
                    if data.get('dwjz'):
                        result.previous_nav = Decimal(str(data.get('dwjz')))

                    # 累计净值 (ljjz)
                    if data.get('ljjz'):
                        result.accumulated_nav = Decimal(str(data.get('ljjz')))

                    # 计算日增长率 (基于昨日净值和估算净值)
                    if result.estimate_nav and result.previous_nav and result.previous_nav > 0:
                        daily_growth = ((result.estimate_nav - result.previous_nav) / result.previous_nav * 100)
                        result.daily_growth = Decimal(str(round(daily_growth, 2)))

                    result.update_time = data.get('gztime', '--')
                    result.status = '正常' if result.estimate_nav else '非交易时段'
                    result.data_source = 'tiantian'

                    self.error_stats['tiantian']['success'] += 1
                else:
                    result.status = '无数据(解析空)'
            else:
                result.status = f'HTTP {resp.status_code}'
        except Exception as e:
            logger.debug(f"天天基金接口失败 {code}: {e}")
            self.error_stats['tiantian']['failure'] += 1
            result.status = '网络错误'

        return result
    
    def _try_sina_lof(self, code: str) -> Optional[FundRealtimeData]:
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
                    
                    return FundRealtimeData(
                        code=code,
                        name=fields[0],
                        estimate_nav=Decimal(str(current_price)),
                        estimate_change=Decimal(str(round(change_pct, 2))),
                        update_time=fields[31] if len(fields) > 31 else '--',
                        status='场内行情',
                        data_source='sina_lof'
                    )
        except Exception as e:
            logger.debug(f"新浪LOF接口失败 {code}: {e}")
        return None
    
    def _try_akshare_lof(self, code: str) -> Optional[FundRealtimeData]:
        """尝试AKShare LOF数据"""
        try:
            import sys
            from io import StringIO
            
            old_stdout = sys.stdout
            sys.stdout = StringIO()
            
            try:
                df = ak.fund_lof_spot_em()
            finally:
                sys.stdout = old_stdout
            
            row = df[df['代码'] == code]
            
            if not row.empty:
                return FundRealtimeData(
                    code=code,
                    name=str(row['名称'].values[0]),
                    estimate_nav=Decimal(str(row['最新价'].values[0])),
                    estimate_change=Decimal(str(row['涨跌幅'].values[0])),
                    update_time='--',
                    status='LOF行情',
                    data_source='akshare_lof'
                )
        except:
            pass
        return None
    
    def _try_latest_nav(self, code: str, name: str) -> Optional[FundRealtimeData]:
        """尝试获取最新净值"""
        try:
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
                return FundRealtimeData(
                    code=code,
                    name=name,
                    estimate_nav=Decimal(str(latest['单位净值'])),
                    estimate_change=None,
                    update_time=latest['净值日期'].strftime('%Y-%m-%d'),
                    status='最新净值',
                    data_source='latest_nav'
                )
        except Exception as e:
            logger.debug(f"获取最新净值失败 {code}: {e}")
        return None
    
    def get_historical_nav(self, code: str, days: int = 365) -> pd.DataFrame:
        """获取历史净值数据"""
        try:
            df = ak.fund_open_fund_info_em(symbol=code, indicator="累计净值走势")
            df['净值日期'] = pd.to_datetime(df['净值日期'])
            df['累计净值'] = pd.to_numeric(df['累计净值'])
            df = df.sort_values('净值日期').reset_index(drop=True)
            df['pct_change'] = df['累计净值'].pct_change().fillna(0)
            
            # 过滤日期范围
            if days > 0:
                start_date = datetime.now() - timedelta(days=days)
                df = df[df['净值日期'] >= start_date]
            
            return df
        except Exception as e:
            print(f"获取历史净值失败 {code}: {e}")
            return pd.DataFrame()
    
    def analyze_trend(self, hist_data: pd.DataFrame, direction: str) -> tuple:
        """分析趋势：返回(连续天数, 累计涨跌幅)"""
        if hist_data.empty:
            return 0, Decimal('0')
        
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
            return 0, Decimal('0')
        
        total_chg = np.prod([1 + r for r in changes]) - 1
        
        if direction == 'down':
            total_chg = -abs(total_chg)
        else:
            total_chg = abs(total_chg)
        
        return days, Decimal(str(total_chg))
    
    def screen_funds(self, codes: List[str], direction: str, 
                     min_days: int, min_pct: Decimal) -> List[FundTrendScreenResult]:
        """筛选符合条件的基金"""
        results = []
        
        for code in codes:
            hist = self.get_historical_nav(code)
            if hist.empty:
                continue
            
            days, total_chg = self.analyze_trend(hist, direction)
            
            if days >= min_days and abs(total_chg) >= min_pct:
                name = self.get_fund_name(code)
                results.append(FundTrendScreenResult(
                    code=code,
                    name=name,
                    days=days,
                    pct=round(total_chg * 100, 2)
                ))
        
        return results
    
    def get_benchmark_data(self, symbol: str, days: int = 365) -> dict:
        """获取基准指数数据"""
        try:
            df = ak.stock_zh_index_daily(symbol=symbol)
            df['date'] = pd.to_datetime(df['date'])
            
            if days > 0:
                start_date = datetime.now() - timedelta(days=days)
                df = df[df['date'] >= start_date]
            
            df = df.sort_values('date')
            
            if df.empty:
                return {"dates": [], "values": [], "changes": []}
            
            start_value = df['close'].iloc[0]
            df['pct_change'] = ((df['close'] - start_value) / start_value * 100).round(2)
            
            dates = df['date'].dt.strftime('%Y-%m-%d').tolist()
            values = [float(v) for v in df['close'].tolist()]
            changes = [float(v) for v in df['pct_change'].tolist()]
            
            return {
                "dates": dates,
                "values": values,
                "changes": changes,
                "start_value": float(start_value)
            }
        except Exception as e:
            logger.error(f"获取基准指数数据失败 {symbol}: {e}")
            return {"dates": [], "values": [], "changes": []}
    
    def get_chart_data(self, code: str, range_str: str = "3M") -> FundChartData:
        """获取图表数据"""
        days = chart_config.TIME_RANGES.get(range_str, {}).get('days', 90)
        
        hist = self.get_historical_nav(code, days)
        
        if hist.empty:
            return FundChartData(dates=[], values=[], changes=[])
        
        dates = hist['净值日期'].dt.strftime('%Y-%m-%d').tolist()
        values = [Decimal(str(v)) for v in hist['累计净值'].tolist()]
        changes = [Decimal(str(v * 100)) if pd.notna(v) else None 
                   for v in hist['pct_change'].tolist()]
        
        return FundChartData(dates=dates, values=values, changes=changes)
    
    def search_funds(self, keyword: str, limit: int = 10) -> List[Dict]:
        """搜索基金"""
        results = []
        
        try:
            # 使用akshare搜索
            df = ak.fund_name_em()
            
            # 模糊匹配
            mask = df['基金简称'].str.contains(keyword, na=False) | \
                   df['基金代码'].str.contains(keyword, na=False)
            matched = df[mask].head(limit)
            
            for _, row in matched.iterrows():
                results.append({
                    'code': row['基金代码'],
                    'name': row['基金简称'],
                    'type': row.get('基金类型', ''),
                    'company': row.get('基金公司', '')
                })
        except Exception as e:
            logger.error(f"搜索基金失败: {e}")
        
        return results


# 单例模式
fund_service = FundDataService()
