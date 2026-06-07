# -*- coding: utf-8 -*-
"""
简化调度器 - 无Redis依赖
保留：实时数据刷新、历史数据增量更新
"""
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
    APSCHEDULER_AVAILABLE = True
except ImportError:
    AsyncIOScheduler = None
    IntervalTrigger = None
    EVENT_JOB_EXECUTED = 0
    EVENT_JOB_ERROR = 0
    APSCHEDULER_AVAILABLE = False

from app.logger import get_logger

logger = get_logger("scheduler")


class SchedulerService:
    def __init__(self):
        self.scheduler: Optional[Any] = None
        self._running = False

    def start(self, refresh_interval_minutes: int = 10):
        if not APSCHEDULER_AVAILABLE:
            logger.warning("apscheduler未安装，后台定时任务已禁用")
            return
        if self._running:
            logger.warning("调度器已在运行")
            return

        self.scheduler = AsyncIOScheduler()
        self.scheduler.add_listener(self._on_job_event, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

        # 实时数据刷新
        self.scheduler.add_job(
            self._refresh_realtime,
            trigger=IntervalTrigger(minutes=refresh_interval_minutes),
            id='refresh_realtime',
            name='刷新实时数据',
            replace_existing=True
        )

        # 历史数据增量更新 - 每天凌晨2点
        self.scheduler.add_job(
            self._update_history,
            trigger='cron',
            hour=2, minute=0,
            id='history_update',
            name='历史数据增量更新',
            replace_existing=True
        )

        self.scheduler.start()
        self._running = True
        logger.info(f"调度器已启动，刷新间隔={refresh_interval_minutes}分钟")

    def shutdown(self):
        if self.scheduler:
            self.scheduler.shutdown(wait=False)
            self._running = False
            logger.info("调度器已关闭")

    def _on_job_event(self, event):
        if event.exception:
            logger.error(f"任务 {event.job_id} 失败: {event.exception}")

    async def _refresh_realtime(self):
        try:
            from app.services.fund_service import get_fund_service
            service = get_fund_service()
            codes = service.get_fund_codes()
            if codes:
                await service.get_realtime_batch(codes)
                logger.info(f"定时刷新 {len(codes)} 只基金完成")
        except Exception as e:
            logger.error(f"定时刷新失败: {e}")

    async def _update_history(self):
        try:
            from app.services.history_service import get_history_service
            from app.services.fund_service import get_fund_service
            service = get_fund_service()
            history = get_history_service()
            codes = service.get_fund_codes()
            for code in codes:
                try:
                    await history.incremental_update(code)
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.error(f"更新 {code} 历史数据失败: {e}")
            logger.info("历史数据增量更新完成")
        except Exception as e:
            logger.error(f"历史数据更新失败: {e}")

    async def trigger_manual_refresh(self, codes: Optional[List[str]] = None) -> Dict[str, Any]:
        from app.services.fund_service import get_fund_service
        service = get_fund_service()
        if not codes:
            codes = service.get_fund_codes()
        result = await service.get_realtime_batch(codes)
        return {
            'success': True,
            'refreshed': len([r for r in result if r.get('nav')]),
            'timestamp': datetime.now().isoformat()
        }

    def get_status(self) -> Dict[str, Any]:
        jobs = []
        if self.scheduler:
            for job in self.scheduler.get_jobs():
                jobs.append({
                    'id': job.id,
                    'name': job.name,
                    'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                })
        return {'running': self._running, 'jobs': jobs}


scheduler_service = SchedulerService()
