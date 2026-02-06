# -*- coding: utf-8 -*-
"""
后台任务调度服务 - 管理定时任务和预加载
"""
import asyncio
from datetime import datetime, timedelta
from typing import Callable, Optional, Dict, Any, List
from dataclasses import dataclass, field

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from app.logger import get_logger
from app.services.cache_service import get_cache_service
from app.services.task_priority import TaskPriority
from app.config import fund_config

logger = get_logger("scheduler_service")


@dataclass
class PreloadTask:
    """预加载任务"""
    fund_code: str
    priority: TaskPriority
    added_at: datetime = field(default_factory=datetime.now)
    retry_count: int = 0
    max_retries: int = 3


class SchedulerService:
    """调度器服务类"""
    
    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.cache = get_cache_service()
        self._preload_queue: List[PreloadTask] = []
        self._is_preloading = False
        self._preload_stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'in_progress': 0
        }
        self._running = False
        
    def start(self):
        """启动调度器"""
        if self._running:
            logger.warning("调度器已在运行")
            return
            
        self.scheduler = AsyncIOScheduler()
        
        # 添加任务监听器
        self.scheduler.add_listener(
            self._on_job_executed,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
        )
        
        # 注册定时任务
        self._register_jobs()
        
        self.scheduler.start()
        self._running = True
        logger.info("✅ 调度器服务已启动")
        
    def shutdown(self):
        """关闭调度器"""
        if self.scheduler:
            self.scheduler.shutdown(wait=False)
            self._running = False
            logger.info("👋 调度器服务已关闭")
            
    def _register_jobs(self):
        """注册定时任务"""
        # 实时数据刷新任务 - 每10分钟
        self.scheduler.add_job(
            self._refresh_realtime_data,
            trigger=IntervalTrigger(minutes=getattr(fund_config, 'REFRESH_INTERVAL_MINUTES', 10)),
            id='refresh_realtime',
            name='刷新实时数据缓存',
            replace_existing=True
        )
        
        # 历史数据增量更新 - 每天凌晨2点
        self.scheduler.add_job(
            self._incremental_history_update,
            trigger='cron',
            hour=2,
            minute=0,
            id='history_update',
            name='历史数据增量更新',
            replace_existing=True
        )
        
        # 缓存统计报告 - 每小时
        self.scheduler.add_job(
            self._report_stats,
            trigger=IntervalTrigger(hours=1),
            id='stats_report',
            name='缓存统计报告',
            replace_existing=True
        )
        
        logger.info(f"📋 已注册 {len(self.scheduler.get_jobs())} 个定时任务")
        
    def _on_job_executed(self, event):
        """任务执行回调"""
        if event.exception:
            logger.error(f"❌ 任务 {event.job_id} 执行失败: {event.exception}")
        else:
            logger.debug(f"✅ 任务 {event.job_id} 执行成功")
            
    async def _refresh_realtime_data(self):
        """刷新实时数据缓存"""
        logger.info("🔄 开始定时刷新实时数据...")
        
        try:
            # 获取所有需要刷新的基金代码
            from app.services.preload_service import preload_service
            codes = preload_service.get_all_tracked_codes()
            
            if not codes:
                logger.info("没有需要刷新的基金")
                return
                
            logger.info(f"准备刷新 {len(codes)} 只基金的实时数据")
            
            # 批量刷新
            await preload_service.batch_refresh_realtime(codes)
            
            logger.info(f"✅ 实时数据刷新完成")
            
        except Exception as e:
            logger.error(f"❌ 刷新实时数据失败: {e}")
            
    async def _incremental_history_update(self):
        """历史数据增量更新"""
        logger.info("🔄 开始历史数据增量更新...")
        
        try:
            from app.services.history_service import history_service
            from app.services.preload_service import preload_service
            
            codes = preload_service.get_all_tracked_codes()
            
            for code in codes:
                try:
                    await history_service.incremental_update(code)
                    await asyncio.sleep(0.5)  # 避免请求过快
                except Exception as e:
                    logger.error(f"更新 {code} 历史数据失败: {e}")
                    
            logger.info("✅ 历史数据增量更新完成")
            
        except Exception as e:
            logger.error(f"❌ 历史数据增量更新失败: {e}")
            
    def _report_stats(self):
        """报告缓存统计"""
        stats = self.cache.get_stats()
        logger.info(f"📊 缓存统计: {stats}")
        
    async def trigger_manual_refresh(self, codes: Optional[List[str]] = None) -> Dict[str, Any]:
        """手动触发刷新"""
        from app.services.preload_service import preload_service
        
        if codes:
            logger.info(f"🔄 手动刷新 {len(codes)} 只基金")
            result = await preload_service.batch_refresh_realtime(codes)
        else:
            logger.info("🔄 手动刷新所有跟踪的基金")
            all_codes = preload_service.get_all_tracked_codes()
            result = await preload_service.batch_refresh_realtime(all_codes)
            
        return {
            'success': True,
            'refreshed': result.get('success', 0),
            'failed': result.get('failed', 0),
            'timestamp': datetime.now().isoformat()
        }
        
    def get_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        jobs = []
        if self.scheduler:
            for job in self.scheduler.get_jobs():
                jobs.append({
                    'id': job.id,
                    'name': job.name,
                    'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger)
                })
                
        return {
            'running': self._running,
            'jobs': jobs,
            'cache_stats': self.cache.get_stats(),
            'preload_stats': self._preload_stats
        }


# 单例模式
scheduler_service = SchedulerService()
