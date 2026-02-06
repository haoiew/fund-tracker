# -*- coding: utf-8 -*-
"""
基金数据源管理模块
实现多数据源并发加载和优先级管理
"""
import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import requests
import akshare as ak
import pandas as pd
from app.logger import get_logger

logger = get_logger("fund_data_source")


class DataSourcePriority(Enum):
    """数据源优先级"""
    HIGH = 1      # 天天基金 - 最可靠
    MEDIUM = 2    # 新浪LOF、AKShare
    LOW = 3       # 最新净值、其他备份


class DataSourceType(Enum):
    """数据源类型"""
    TIANTIAN = "天天基金"
    SINA_LOF = "新浪LOF"
    AKSHARE_LOF = "AKShare LOF"
    LATEST_NAV = "最新净值"
    TENCENT = "腾讯基金"
    EASTMONEY = "东方财富"
    XUEQIU = "雪球"
    HOWBUY = "好买基金"


@dataclass
class DataSourceResult:
    """数据源结果"""
    source_type: DataSourceType
    priority: DataSourcePriority
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    is_valid: bool = True
    error_msg: str = ""
    
    def is_fresh(self, max_age_minutes: int = 60) -> bool:
        """检查数据是否新鲜"""
        age = (datetime.now() - self.timestamp).total_seconds() / 60
        return age <= max_age_minutes


class FundDataSourceManager:
    """
    基金数据源管理器
    实现多数据源并发加载和智能选择
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # 数据源可靠性评分（动态调整）
        self.source_reliability: Dict[DataSourceType, float] = {
            DataSourceType.TIANTIAN: 0.95,
            DataSourceType.SINA_LOF: 0.85,
            DataSourceType.AKSHARE_LOF: 0.80,
            DataSourceType.LATEST_NAV: 0.70,
            DataSourceType.TENCENT: 0.75,
            DataSourceType.XUEQIU: 0.75,
            DataSourceType.HOWBUY: 0.70,
        }
    
    async def fetch_all_sources(self, code: str, name: str) -> List[DataSourceResult]:
        """
        并发获取所有数据源
        
        Args:
            code: 基金代码
            name: 基金名称
            
        Returns:
            所有数据源的结果列表
        """
        # 定义所有数据源任务
        tasks = [
            self._fetch_with_timeout(self._try_tiantian_fund, code, name, DataSourceType.TIANTIAN, DataSourcePriority.HIGH),
            self._fetch_with_timeout(self._try_tencent_fund, code, name, DataSourceType.TENCENT, DataSourcePriority.MEDIUM),
            self._fetch_with_timeout(self._try_eastmoney, code, name, DataSourceType.EASTMONEY, DataSourcePriority.MEDIUM),
        ]
        
        # LOF基金添加场内行情数据源
        if code.startswith(('16', '50', '51')):
            tasks.extend([
                self._fetch_with_timeout(self._try_sina_lof, code, name, DataSourceType.SINA_LOF, DataSourcePriority.MEDIUM),
                self._fetch_with_timeout(self._try_akshare_lof, code, name, DataSourceType.AKSHARE_LOF, DataSourcePriority.MEDIUM),
            ])
        
        # 添加备份数据源
        tasks.extend([
            self._fetch_with_timeout(self._try_latest_nav, code, name, DataSourceType.LATEST_NAV, DataSourcePriority.LOW),
        ])
        
        # 并发执行所有任务
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 过滤有效结果
        valid_results = []
        for result in results:
            if isinstance(result, DataSourceResult) and result.is_valid:
                valid_results.append(result)
            elif isinstance(result, Exception):
                logger.debug(f"数据源获取异常: {result}")
        
        return valid_results
    
    async def _fetch_with_timeout(
        self,
        fetch_func,
        code: str,
        name: str,
        source_type: DataSourceType,
        priority: DataSourcePriority,
        timeout: float = 3.0
    ) -> DataSourceResult:
        """带超时的数据获取"""
        try:
            # 使用 asyncio.wait_for 包装同步请求
            loop = asyncio.get_event_loop()
            data = await asyncio.wait_for(
                loop.run_in_executor(None, fetch_func, code, name),
                timeout=timeout
            )
            
            if data and data.get('status') not in ['无数据', '获取失败', '网络错误', '无实时数据']:
                return DataSourceResult(
                    source_type=source_type,
                    priority=priority,
                    data=data,
                    is_valid=True
                )
            else:
                return DataSourceResult(
                    source_type=source_type,
                    priority=priority,
                    data=data or {},
                    is_valid=False,
                    error_msg="无效数据"
                )
        except asyncio.TimeoutError:
            return DataSourceResult(
                source_type=source_type,
                priority=priority,
                data={},
                is_valid=False,
                error_msg="请求超时"
            )
        except Exception as e:
            return DataSourceResult(
                source_type=source_type,
                priority=priority,
                data={},
                is_valid=False,
                error_msg=str(e)
            )
    
    def select_best_data(self, results: List[DataSourceResult]) -> Tuple[DataSourceResult, List[DataSourceResult]]:
        """
        选择最佳数据源
        
        策略：
        1. 优先选择高优先级且数据新鲜的数据源
        2. 如果高优先级数据源失效或数据超过1小时，使用次优数据源
        3. 返回最佳数据源和所有备选数据源
        """
        if not results:
            return None, []
        
        # 按优先级和可靠性排序
        def sort_key(r: DataSourceResult):
            reliability = self.source_reliability.get(r.source_type, 0.5)
            is_fresh = r.is_fresh(max_age_minutes=60)
            # 新鲜数据加分，不新鲜的数据减分
            freshness_score = 1.0 if is_fresh else 0.3
            return (r.priority.value, -reliability * freshness_score)
        
        sorted_results = sorted(results, key=sort_key)
        best = sorted_results[0] if sorted_results else None
        alternatives = sorted_results[1:] if len(sorted_results) > 1 else []
        
        return best, alternatives
    
    def _try_tiantian_fund(self, code: str, name: str) -> Dict:
        """天天基金实时估值"""
        item = {
            'code': code, 'name': name, 'gz': None, 'gszzl': None,
            'dwjz': None, 'time': '--', 'status': '获取中',
            'source': '天天基金'
        }
        try:
            ts = int(time.time() * 1000)
            url = f"http://fundgz.1234567.com.cn/js/{code}.js?rt={ts}"
            resp = self.session.get(url, timeout=3)
            if resp.status_code == 200 and resp.text:
                text = resp.text.replace("jsonpgz(", "").replace(");", "").strip()
                if text:
                    data = json.loads(text)
                    if 'name' in data and data['name']:
                        item['name'] = data['name']
                    item['gz'] = data.get('gsz')
                    item['gszzl'] = data.get('gszzl')
                    item['dwjz'] = data.get('dwjz')
                    item['time'] = data.get('gztime', '--')
                    # 只有真正有净值数据时才返回正常状态
                    if item['gz'] and float(item['gz']) > 0:
                        item['status'] = '正常'
                        return item
                    else:
                        # 无实时估值数据，标记为无效以便降级到其他数据源
                        item['status'] = '无实时数据'
                        return item
            item['status'] = '无数据'
        except Exception as e:
            logger.debug(f"天天基金接口失败 {code}: {e}")
            item['status'] = '网络错误'
        return item
    
    def _try_tencent_fund(self, code: str, name: str) -> Dict:
        """腾讯基金接口 - 支持QDII基金"""
        item = {
            'code': code, 'name': name, 'gz': None, 'gszzl': None,
            'time': '--', 'status': '获取中',
            'source': '腾讯基金'
        }
        try:
            url = f"http://qt.gtimg.cn/q=jj{code}"
            resp = self.session.get(url, timeout=2)
            if resp.status_code == 200 and "v_jj" in resp.text:
                content = resp.text.split('="')[1].strip('";\n')
                parts = content.split('~')
                if len(parts) > 8:
                    # 腾讯接口字段解析:
                    # 0:代码 1:名称 2:最新价 3:昨收 4:今开 5:净值(QDII) 6:累计净值 7:涨跌幅 8:日期
                    item['name'] = parts[1] if parts[1] else name
                    
                    price_str = parts[2].strip() if parts[2] else ''
                    nav_str = parts[5].strip() if len(parts) > 5 and parts[5] else ''  # QDII基金净值字段
                    change_str = parts[7].strip() if len(parts) > 7 and parts[7] else ''
                    
                    # 优先使用最新价，如果为0或空则使用净值字段(QDII基金)
                    if price_str and price_str not in ['0.00', '0.0000', '0', '']:
                        try:
                            item['gz'] = float(price_str)
                        except ValueError:
                            pass
                    elif nav_str and nav_str not in ['0.00', '0.0000', '0', '']:
                        try:
                            item['gz'] = float(nav_str)
                        except ValueError:
                            pass
                    
                    # 涨跌幅
                    if change_str and change_str not in ['0.00', '0.0000', '0', '']:
                        try:
                            item['gszzl'] = float(change_str)
                        except ValueError:
                            pass
                    
                    # 只要有净值或涨跌幅，就认为是有效数据
                    if item['gz'] is not None or item['gszzl'] is not None:
                        item['time'] = parts[8] if len(parts) > 8 and parts[8] else datetime.now().strftime('%H:%M:%S')
                        item['status'] = '正常'
                        return item
                    
                    # 无有效数据
                    item['status'] = '无实时数据'
                    return item
            item['status'] = '无数据'
        except Exception as e:
            logger.debug(f"腾讯基金接口失败 {code}: {e}")
            item['status'] = '网络错误'
        return item
    
    def _try_sina_lof(self, code: str, name: str) -> Dict:
        """新浪LOF场内行情"""
        item = {
            'code': code, 'name': name, 'gz': None, 'gszzl': None,
            'time': '--', 'status': '获取中',
            'source': '新浪LOF'
        }
        try:
            # 尝试深圳LOF
            url = f"http://hq.sinajs.cn/list=sz{code}"
            resp = self.session.get(url, timeout=2)
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
                        'status': '场内行情',
                        'source': '新浪LOF'
                    }
            item['status'] = '无数据'
        except Exception as e:
            logger.debug(f"新浪LOF接口失败 {code}: {e}")
            item['status'] = '网络错误'
        return item
    
    def _try_akshare_lof(self, code: str, name: str) -> Dict:
        """AKShare LOF数据"""
        item = {
            'code': code, 'name': name, 'gz': None, 'gszzl': None,
            'time': '--', 'status': '获取中',
            'source': 'AKShare LOF'
        }
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
                return {
                    'code': code, 'name': str(row['名称'].values[0]),
                    'gz': float(row['最新价'].values[0]),
                    'gszzl': float(row['涨跌幅'].values[0]),
                    'time': '--', 'status': 'LOF行情',
                    'source': 'AKShare LOF'
                }
            item['status'] = '无数据'
        except Exception as e:
            logger.debug(f"AKShare LOF接口失败 {code}: {e}")
            item['status'] = '网络错误'
        return item
    
    def _try_eastmoney(self, code: str, name: str) -> Dict:
        """东方财富数据源 - 提供历史净值和涨跌幅"""
        item = {
            'code': code, 'name': name, 'gz': None, 'gszzl': None,
            'time': '--', 'status': '获取中',
            'source': '东方财富'
        }
        try:
            url = f"http://fund.eastmoney.com/pingzhongdata/{code}.js"
            resp = self.session.get(url, timeout=5)
            if resp.status_code == 200:
                content = resp.text
                
                # 提取净值历史数据
                match = re.search(r'var Data_netWorthTrend = (\[.*?\]);', content, re.DOTALL)
                if match:
                    data = json.loads(match.group(1))
                    if len(data) >= 2:
                        latest = data[-1]
                        prev = data[-2]
                        
                        item['gz'] = latest.get('y')  # 最新净值
                        item['time'] = latest.get('x')  # 时间戳
                        
                        # 计算日涨跌幅
                        prev_val = prev.get('y', 0)
                        if prev_val > 0:
                            item['gszzl'] = round((latest['y'] - prev_val) / prev_val * 100, 2)
                        
                        item['status'] = '正常'
                        return item
                
                item['status'] = '无历史数据'
            else:
                item['status'] = '请求失败'
        except Exception as e:
            logger.debug(f"东方财富接口失败 {code}: {e}")
            item['status'] = '网络错误'
        return item
    
    def _try_latest_nav(self, code: str, name: str) -> Dict:
        """最新净值降级"""
        item = {
            'code': code, 'name': name, 'gz': None, 'gszzl': None,
            'time': '--', 'status': '获取中',
            'source': '最新净值'
        }
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
                return {
                    'code': code, 'name': name,
                    'gz': float(latest['单位净值']),
                    'gszzl': None,
                    'time': latest['净值日期'].strftime('%Y-%m-%d'),
                    'status': '最新净值',
                    'source': '最新净值'
                }
            item['status'] = '无数据'
        except Exception as e:
            logger.debug(f"获取最新净值失败 {code}: {e}")
            item['status'] = '网络错误'
        return item


# 全局数据源管理器实例
data_source_manager = FundDataSourceManager()


def get_data_source_manager() -> FundDataSourceManager:
    """获取数据源管理器实例"""
    return data_source_manager
