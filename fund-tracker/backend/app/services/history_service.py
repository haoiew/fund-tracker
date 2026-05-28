# -*- coding: utf-8 -*-
"""
历史数据管理服务 - 本地持久化缓存和增量更新
"""
import asyncio
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Any
from decimal import Decimal
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.db.base import SessionLocal
from app.models.fund import Fund, FundNavHistory
from app.core.cache import get_cache
from app.config import settings
from app.logger import get_logger

logger = get_logger("history_service")


class HistoryService:
    def __init__(self):
        self.cache = get_cache()
        self._update_locks: Dict[str, asyncio.Lock] = {}
        self._background_tasks: set = set()

    def _get_lock(self, code: str) -> asyncio.Lock:
        if code not in self._update_locks:
            # Prevent unbounded growth: clear locks if too many accumulate
            if len(self._update_locks) > 200:
                self._update_locks.clear()
            self._update_locks[code] = asyncio.Lock()
        return self._update_locks[code]

    async def get_chart_data_with_fallback(self, code: str, range_str: str = "3M") -> Dict[str, Any]:
        days = settings.TIME_RANGES.get(range_str, {}).get('days', 90)

        # 优先本地数据库
        local_data = await self._get_local_data(code, days)
        if local_data and len(local_data.get('dates', [])) > 10:
            logger.info(f"本地缓存命中: {code}, {len(local_data['dates'])} 条")
            task = asyncio.create_task(self._background_update(code, days))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
            return {'data': local_data, 'source': 'local', 'updating': True}

        # 本地无数据，联网获取
        fresh_data = await self._fetch_and_store(code, days)
        return {'data': fresh_data, 'source': 'fresh', 'updating': False}

    async def _get_local_data(self, code: str, days: int) -> Optional[Dict[str, Any]]:
        try:
            db = SessionLocal()
            try:
                start_date = datetime.now().date() - timedelta(days=days) if days > 0 else date(2000, 1, 1)
                query = db.query(FundNavHistory).filter(
                    and_(FundNavHistory.fund_code == code, FundNavHistory.nav_date >= start_date)
                ).order_by(FundNavHistory.nav_date.asc()).all()

                if not query:
                    return None

                dates, values, changes = [], [], []
                for i, record in enumerate(query):
                    dates.append(record.nav_date.strftime('%Y-%m-%d'))
                    values.append(record.accum_nav if record.accum_nav else record.nav)
                    if i > 0 and values[i-1] and values[i]:
                        change = ((values[i] - values[i-1]) / values[i-1] * 100)
                        changes.append(Decimal(str(round(change, 2))))
                    else:
                        changes.append(None)

                return {'dates': dates, 'values': values, 'changes': changes}
            finally:
                db.close()
        except Exception as e:
            logger.error(f"获取本地数据失败 {code}: {e}")
            return None

    async def _background_update(self, code: str, days: int):
        async with self._get_lock(code):
            try:
                last_date = await self._get_last_update_date(code)
                if last_date and (datetime.now().date() - last_date).days < 1:
                    return
                await self._fetch_and_store(code, days)
            except Exception as e:
                logger.error(f"后台更新失败 {code}: {e}")

    async def _get_last_update_date(self, code: str) -> Optional[date]:
        try:
            db = SessionLocal()
            try:
                result = db.query(FundNavHistory).filter(
                    FundNavHistory.fund_code == code
                ).order_by(FundNavHistory.nav_date.desc()).first()
                return result.nav_date if result else None
            finally:
                db.close()
        except Exception as e:
            logger.error(f"获取最后更新日期失败 {code}: {e}")
            return None

    async def _fetch_and_store(self, code: str, days: int) -> Dict[str, Any]:
        try:
            from app.services.fund_service import get_fund_service
            fund_service = get_fund_service()
            df = await asyncio.get_event_loop().run_in_executor(
                None, fund_service.get_historical_nav, code, days
            )

            if df.empty:
                return {'dates': [], 'values': [], 'changes': []}

            await self._store_to_db(code, df)

            dates = df['净值日期'].dt.strftime('%Y-%m-%d').tolist()
            values = [Decimal(str(v)) for v in df['累计净值'].tolist()]
            changes = [Decimal(str(v * 100)) if pd.notna(v) else None for v in df['pct_change'].tolist()]

            return {'dates': dates, 'values': values, 'changes': changes}
        except Exception as e:
            logger.error(f"获取并存储数据失败 {code}: {e}")
            return {'dates': [], 'values': [], 'changes': []}

    def _ensure_fund_exists(self, db: Session, code: str):
        """Ensure a Fund record exists before inserting nav history."""
        existing = db.query(Fund).filter(Fund.code == code).first()
        if existing:
            return
        try:
            from app.services.fund_service import get_fund_service
            fund_name = get_fund_service().get_fund_name(code)
        except Exception:
            fund_name = code
        savepoint = db.begin_nested()
        try:
            fund = Fund(code=code, name=fund_name)
            db.add(fund)
            savepoint.commit()
            db.flush()
        except Exception:
            savepoint.rollback()
            # Fund may have been created by another process
            existing = db.query(Fund).filter(Fund.code == code).first()
            if not existing:
                raise

    async def _store_to_db(self, code: str, df: pd.DataFrame):
        if df.empty:
            return
        db = SessionLocal()
        try:
            self._ensure_fund_exists(db, code)

            # Batch query existing records for this fund
            dates_in_df = []
            for _, row in df.iterrows():
                nav_date = row['净值日期']
                if isinstance(nav_date, pd.Timestamp):
                    nav_date = nav_date.date()
                dates_in_df.append(nav_date)

            existing_records = db.query(FundNavHistory).filter(
                and_(FundNavHistory.fund_code == code, FundNavHistory.nav_date.in_(dates_in_df))
            ).all()
            existing_map = {r.nav_date: r for r in existing_records}

            for _, row in df.iterrows():
                nav_date = row['净值日期']
                if isinstance(nav_date, pd.Timestamp):
                    nav_date = nav_date.date()

                daily_change = row.get('pct_change', 0) * 100 if pd.notna(row.get('pct_change')) else None
                existing = existing_map.get(nav_date)

                if existing:
                    existing.nav = row.get('单位净值')
                    existing.accum_nav = row.get('累计净值')
                    existing.daily_change = daily_change
                else:
                    db.add(FundNavHistory(
                        fund_code=code, nav_date=nav_date,
                        nav=row.get('单位净值'), accum_nav=row.get('累计净值'),
                        daily_change=daily_change
                    ))
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"存储数据失败 {code}: {e}")
        finally:
            db.close()

    async def incremental_update(self, code: str) -> Dict[str, Any]:
        async with self._get_lock(code):
            try:
                last_date = await self._get_last_update_date(code)
                if not last_date:
                    result = await self._fetch_and_store(code, settings.HISTORY_CACHE_DAYS)
                    return {'code': code, 'full_update': True, 'records': len(result.get('dates', []))}

                days_to_fetch = (datetime.now().date() - last_date).days + 5
                if days_to_fetch <= 0:
                    return {'code': code, 'updated': 0}

                from app.services.fund_service import get_fund_service
                fund_service = get_fund_service()
                df = await asyncio.get_event_loop().run_in_executor(
                    None, fund_service.get_historical_nav, code, days_to_fetch
                )

                if df.empty:
                    return {'code': code, 'updated': 0}

                df = df[df['净值日期'] > pd.Timestamp(last_date)]
                if df.empty:
                    return {'code': code, 'updated': 0}

                await self._store_to_db(code, df)
                return {'code': code, 'updated': len(df), 'from_date': last_date.isoformat()}
            except Exception as e:
                logger.error(f"增量更新失败 {code}: {e}")
                return {'code': code, 'error': str(e)}

    async def warmup_history_cache(self, codes: List[str], days: int = 365):
        results = []
        for code in codes:
            try:
                result = await self._fetch_and_store(code, days)
                results.append({'code': code, 'records': len(result.get('dates', []))})
                await asyncio.sleep(0.5)
            except Exception as e:
                results.append({'code': code, 'error': str(e)})
        return results

    def get_cache_status(self, code: str) -> Dict[str, Any]:
        try:
            db = SessionLocal()
            try:
                count = db.query(FundNavHistory).filter(FundNavHistory.fund_code == code).count()
                first = db.query(FundNavHistory).filter(FundNavHistory.fund_code == code).order_by(FundNavHistory.nav_date.asc()).first()
                last = db.query(FundNavHistory).filter(FundNavHistory.fund_code == code).order_by(FundNavHistory.nav_date.desc()).first()
                return {
                    'code': code, 'cached_records': count,
                    'date_range': {'from': first.nav_date.isoformat() if first else None, 'to': last.nav_date.isoformat() if last else None}
                }
            finally:
                db.close()
        except Exception as e:
            return {'code': code, 'error': str(e)}


_history_service: Optional[HistoryService] = None


def get_history_service() -> HistoryService:
    global _history_service
    if _history_service is None:
        _history_service = HistoryService()
    return _history_service
