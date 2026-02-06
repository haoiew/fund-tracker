# -*- coding: utf-8 -*-
"""
数据预加载服务 - 按优先级批量加载基金数据
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set, Any
from collections import defaultdict
import time

from app.services.fund_service import fund_service
from app.services.cache_service import get_cache_service
from app.services.task_priority import TaskPriority
from app.config import fund_config
from app.logger import get_logger

logger = get_logger("preload_service")


class PreloadService:
    """预加载服务类"""
    
    def __init__(self):
        self.cache = get_cache_service()
        self._tracked_codes: Set[str] = set()  # 所有跟踪的基金代码
        self._user_portfolio: Set[str] = set()  # 用户持仓
        self._recently_viewed: Set[str] = set()  # 最近访问
        self._preload_stats = {
            'total_preloaded': 0,
            'success_count': 0,
            'failed_count': 0,
            'last_preload_time': None
        }
        self._concurrent_limit = getattr(fund_config, 'PRELOAD_CONCURRENT', 5)
        self._semaphore = asyncio.Semaphore(self._concurrent_limit)
        
    def get_all_tracked_codes(self) -> List[str]:
        """获取所有跟踪的基金代码"""
        return list(self._tracked_codes)
        
    def add_to_portfolio(self, code: str):
        """添加用户持仓基金"""
        self._user_portfolio.add(code)
        self._tracked_codes.add(code)
        logger.info(f"添加持仓基金: {code}")
        
    def remove_from_portfolio(self, code: str):
        """移除用户持仓基金"""
        self._user_portfolio.discard(code)
        logger.info(f"移除持仓基金: {code}")
        
    def add_recently_viewed(self, code: str):
        """添加最近访问基金"""
        self._recently_viewed.add(code)
        self._tracked_codes.add(code)
        # 限制最近访问列表大小
        if len(self._recently_viewed) > 50:
            self._recently_viewed.pop()
            
    def get_priority_codes(self) -> Dict[TaskPriority, List[str]]:
        """按优先级获取基金代码"""
        priority_map = defaultdict(list)
        
        # P0: 用户持仓
        for code in self._user_portfolio:
            priority_map[TaskPriority.P0].append(code)
            
        # P1: 默认基金列表
        default_funds = set(getattr(fund_config, 'DEFAULT_FUNDS', []))
        for code in default_funds - self._user_portfolio:
            priority_map[TaskPriority.P1].append(code)
            
        # P2: 最近访问
        for code in self._recently_viewed - self._user_portfolio - default_funds:
            priority_map[TaskPriority.P2].append(code)
            
        return dict(priority_map)
        
    async def start_preload(self):
        """启动预加载"""
        logger.info("🚀 开始数据预加载...")
        start_time = time.time()
        
        # 首先加载默认基金
        default_funds = getattr(fund_config, 'DEFAULT_FUNDS', [])
        self._tracked_codes.update(default_funds)
        
        priority_map = self.get_priority_codes()
        
        total_loaded = 0
        
        # 按优先级顺序加载
        for priority in [TaskPriority.P0, TaskPriority.P1, TaskPriority.P2]:
            codes = priority_map.get(priority, [])
            if not codes:
                continue
                
            logger.info(f"📦 优先级 {priority.name}: 加载 {len(codes)} 只基金")
            
            # 根据优先级设置延迟
            if priority == TaskPriority.P1:
                await asyncio.sleep(2)
            elif priority == TaskPriority.P2:
                await asyncio.sleep(5)
                
            result = await self._preload_batch(codes)
            total_loaded += result['success']
            
        elapsed = time.time() - start_time
        self._preload_stats['total_preloaded'] = total_loaded
        self._preload_stats['last_preload_time'] = datetime.now().isoformat()
        
        logger.info(f"✅ 预加载完成: {total_loaded} 只基金, 耗时 {elapsed:.2f}s")
        
    async def _preload_batch(self, codes: List[str]) -> Dict[str, int]:
        """批量预加载"""
        success = 0
        failed = 0
        
        async def load_one(code: str):
            nonlocal success, failed
            async with self._semaphore:
                try:
                    # 检查是否已缓存且未过期
                    cache_key = f"realtime:{code}"
                    cached = self.cache.get(cache_key)
                    
                    if cached:
                        # 检查缓存时间
                        cached_at = cached.get('cached_at')
                        if cached_at:
                            cache_time = datetime.fromisoformat(cached_at)
                            if datetime.now() - cache_time < timedelta(minutes=5):
                                logger.debug(f"⏭️ 跳过已缓存: {code}")
                                return
                    
                    # 获取数据
                    data = await asyncio.get_event_loop().run_in_executor(
                        None, fund_service.get_realtime_data, code
                    )
                    
                    # 添加缓存时间戳
                    data_dict = data.model_dump(mode='json')
                    data_dict['cached_at'] = datetime.now().isoformat()
                    
                    # 写入缓存
                    ttl = getattr(fund_config, 'REALTIME_CACHE_TTL', 60)
                    self.cache.set(cache_key, data_dict, ttl)
                    
                    success += 1
                    logger.debug(f"✅ 预加载成功: {code}")
                    
                except Exception as e:
                    failed += 1
                    logger.warning(f"❌ 预加载失败 {code}: {e}")
                    
        # 并发执行
        await asyncio.gather(*[load_one(code) for code in codes])
        
        self._preload_stats['success_count'] += success
        self._preload_stats['failed_count'] += failed
        
        return {'success': success, 'failed': failed}
        
    async def batch_refresh_realtime(self, codes: List[str]) -> Dict[str, Any]:
        """批量刷新实时数据"""
        if not codes:
            return {'success': 0, 'failed': 0}
            
        logger.info(f"🔄 批量刷新 {len(codes)} 只基金")
        
        result = await self._preload_batch(codes)
        
        logger.info(f"✅ 刷新完成: {result['success']} 成功, {result['failed']} 失败")
        
        return {
            'success': result['success'],
            'failed': result['failed'],
            'timestamp': datetime.now().isoformat()
        }
        
    async def warmup_cache(self, codes: List[str], priority: TaskPriority = TaskPriority.P3):
        """预热缓存"""
        logger.info(f"🔥 预热缓存: {len(codes)} 只基金, 优先级 {priority.name}")
        
        self._tracked_codes.update(codes)
        
        result = await self._preload_batch(codes)
        
        return {
            'warmed': result['success'],
            'failed': result['failed'],
            'priority': priority.name
        }
        
    def get_stats(self) -> Dict[str, Any]:
        """获取预加载统计"""
        return {
            **self._preload_stats,
            'tracked_count': len(self._tracked_codes),
            'portfolio_count': len(self._user_portfolio),
            'recent_count': len(self._recently_viewed),
            'concurrent_limit': self._concurrent_limit
        }
        
    def get_priority_summary(self) -> Dict[str, List[str]]:
        """获取优先级摘要"""
        priority_map = self.get_priority_codes()
        return {
            priority.name: codes 
            for priority, codes in priority_map.items()
        }


# 单例模式
preload_service = PreloadService()
