# -*- coding: utf-8 -*-
"""
历史数据管理服务 - 本地持久化缓存和增量更新
"""
import asyncio
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Any, Tuple
from decimal import Decimal
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.db.base import SessionLocal
from app.models.fund import FundNavHistory
from app.schemas.fund import FundChartData
from app.services.cache_service import get_cache_service
from app.config import fund_config, chart_config
from app.logger import get_logger

logger = get_logger("history_service")


class HistoryService:
    """历史数据服务类"""
    
    def __init__(self):
        self.cache = get_cache_service()
        self._update_locks: Dict[str, asyncio.Lock] = {}
        
    def _get_lock(self, code: str) -> asyncio.Lock:
        """获取基金更新锁"""
        if code not in self._update_locks:
            self._update_locks[code] = asyncio.Lock()
        return self._update_locks[code]
        
    async def get_chart_data_with_fallback(
        self,
        code: str,
        range_str: str = "3M",
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        获取图表数据（本地优先，秒级响应）

        策略：
        1. 优先从本地SQLite数据库读取（<100ms）
        2. 本地有数据立即返回，后台异步检查更新
        3. 本地无数据才联网获取
        """
        days = chart_config.TIME_RANGES.get(range_str, {}).get('days', 90)

        # 1. 首先尝试从本地数据库获取（优先保证速度）
        local_data = await self._get_local_data(code, days)

        if local_data and len(local_data.get('dates', [])) > 10:  # 至少10条数据才认为有效
            # 有本地数据，立即返回（秒级响应）
            logger.info(f"⚡ 本地缓存命中: {code}, {len(local_data['dates'])} 条, 范围: {range_str}")

            # 后台异步检查是否需要更新（不阻塞响应）
            asyncio.create_task(self._background_update(code, days))

            return {
                'data': local_data,
                'source': 'local',
                'updating': True
            }

        # 2. 本地无数据或数据不足，才联网获取
        logger.info(f"🌐 本地无数据，联网获取: {code}")
        fresh_data = await self._fetch_and_store(code, days)

        return {
            'data': fresh_data,
            'source': 'fresh',
            'updating': False
        }
        
    async def _get_local_data(self, code: str, days: int) -> Optional[Dict[str, Any]]:
        """从本地数据库获取数据"""
        try:
            db = SessionLocal()
            try:
                # 计算起始日期
                start_date = datetime.now().date() - timedelta(days=days) if days > 0 else date(2000, 1, 1)
                
                # 查询数据库
                query = db.query(FundNavHistory).filter(
                    and_(
                        FundNavHistory.fund_code == code,
                        FundNavHistory.nav_date >= start_date
                    )
                ).order_by(FundNavHistory.nav_date.asc()).all()
                
                if not query:
                    return None
                
                dates = []
                values = []
                changes = []
                
                for i, record in enumerate(query):
                    dates.append(record.nav_date.strftime('%Y-%m-%d'))
                    values.append(record.accum_nav if record.accum_nav else record.nav)
                    
                    # 计算涨跌幅
                    if i > 0 and values[i-1] and values[i]:
                        change = ((values[i] - values[i-1]) / values[i-1] * 100)
                        changes.append(Decimal(str(round(change, 2))))
                    else:
                        changes.append(None)
                
                return {
                    'dates': dates,
                    'values': values,
                    'changes': changes
                }
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"获取本地数据失败 {code}: {e}")
            return None
            
    async def _background_update(self, code: str, days: int):
        """后台更新数据"""
        async with self._get_lock(code):
            try:
                # 检查最后更新日期
                last_date = await self._get_last_update_date(code)
                
                if last_date:
                    days_since_update = (datetime.now().date() - last_date).days
                    if days_since_update < 1:
                        logger.debug(f"⏭️ 数据已最新: {code}, 最后更新 {last_date}")
                        return
                
                logger.info(f"🔄 后台更新数据: {code}")
                await self._fetch_and_store(code, days)
                logger.info(f"✅ 后台更新完成: {code}")
                
            except Exception as e:
                logger.error(f"后台更新失败 {code}: {e}")
                
    async def _get_last_update_date(self, code: str) -> Optional[date]:
        """获取最后更新日期"""
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
        """获取数据并存储到本地"""
        try:
            # 使用 fund_service 获取历史数据
            from app.services.fund_service import fund_service
            
            df = await asyncio.get_event_loop().run_in_executor(
                None, fund_service.get_historical_nav, code, days
            )
            
            if df.empty:
                logger.warning(f"获取历史数据为空: {code}")
                return {'dates': [], 'values': [], 'changes': []}
            
            # 存储到数据库
            await self._store_to_db(code, df)
            
            # 转换为响应格式
            dates = df['净值日期'].dt.strftime('%Y-%m-%d').tolist()
            values = [Decimal(str(v)) for v in df['累计净值'].tolist()]
            changes = [Decimal(str(v * 100)) if pd.notna(v) else None 
                      for v in df['pct_change'].tolist()]
            
            return {
                'dates': dates,
                'values': values,
                'changes': changes
            }
            
        except Exception as e:
            logger.error(f"获取并存储数据失败 {code}: {e}")
            return {'dates': [], 'values': [], 'changes': []}
            
    async def _store_to_db(self, code: str, df: pd.DataFrame):
        """存储数据到数据库"""
        if df.empty:
            return
            
        db = SessionLocal()
        try:
            stored_count = 0
            
            for _, row in df.iterrows():
                nav_date = row['净值日期']
                if isinstance(nav_date, pd.Timestamp):
                    nav_date = nav_date.date()
                
                # 检查是否已存在
                existing = db.query(FundNavHistory).filter(
                    and_(
                        FundNavHistory.fund_code == code,
                        FundNavHistory.nav_date == nav_date
                    )
                ).first()
                
                if existing:
                    # 更新现有记录
                    existing.nav = row.get('单位净值')
                    existing.accum_nav = row.get('累计净值')
                    existing.daily_change = row.get('pct_change', 0) * 100 if pd.notna(row.get('pct_change')) else None
                else:
                    # 创建新记录
                    history = FundNavHistory(
                        fund_code=code,
                        nav_date=nav_date,
                        nav=row.get('单位净值'),
                        accum_nav=row.get('累计净值'),
                        daily_change=row.get('pct_change', 0) * 100 if pd.notna(row.get('pct_change')) else None
                    )
                    db.add(history)
                
                stored_count += 1
            
            db.commit()
            logger.info(f"💾 存储历史数据: {code}, {stored_count} 条")
            
        except Exception as e:
            db.rollback()
            logger.error(f"存储数据失败 {code}: {e}")
        finally:
            db.close()
            
    async def incremental_update(self, code: str) -> Dict[str, Any]:
        """增量更新历史数据"""
        logger.info(f"📈 增量更新: {code}")
        
        async with self._get_lock(code):
            try:
                # 获取最后更新日期
                last_date = await self._get_last_update_date(code)
                
                if not last_date:
                    # 无历史数据，全量获取
                    logger.info(f"无历史数据，执行全量更新: {code}")
                    result = await self._fetch_and_store(code, 365 * 2)  # 2年
                    return {
                        'code': code,
                        'full_update': True,
                        'records': len(result.get('dates', []))
                    }
                
                # 计算需要更新的天数
                days_to_fetch = (datetime.now().date() - last_date).days + 5  # 多取5天确保覆盖
                
                if days_to_fetch <= 0:
                    logger.info(f"数据已最新: {code}")
                    return {'code': code, 'updated': 0}
                
                # 获取新数据
                from app.services.fund_service import fund_service
                
                df = await asyncio.get_event_loop().run_in_executor(
                    None, fund_service.get_historical_nav, code, days_to_fetch
                )
                
                if df.empty:
                    return {'code': code, 'updated': 0}
                
                # 只保留新数据
                df = df[df['净值日期'] > pd.Timestamp(last_date)]
                
                if df.empty:
                    logger.info(f"无新数据: {code}")
                    return {'code': code, 'updated': 0}
                
                # 存储新数据
                await self._store_to_db(code, df)
                
                updated_count = len(df)
                logger.info(f"✅ 增量更新完成: {code}, 新增 {updated_count} 条")
                
                return {
                    'code': code,
                    'updated': updated_count,
                    'from_date': last_date.isoformat(),
                    'to_date': df['净值日期'].max().strftime('%Y-%m-%d')
                }
                
            except Exception as e:
                logger.error(f"增量更新失败 {code}: {e}")
                return {'code': code, 'error': str(e)}
                
    async def warmup_history_cache(self, codes: List[str], days: int = 365):
        """预热历史数据缓存"""
        logger.info(f"🔥 预热历史数据: {len(codes)} 只基金, {days} 天")
        
        results = []
        for code in codes:
            try:
                result = await self._fetch_and_store(code, days)
                results.append({
                    'code': code,
                    'records': len(result.get('dates', []))
                })
                await asyncio.sleep(0.5)  # 避免请求过快
            except Exception as e:
                logger.error(f"预热失败 {code}: {e}")
                results.append({'code': code, 'error': str(e)})
        
        total_records = sum(r.get('records', 0) for r in results if 'records' in r)
        logger.info(f"✅ 历史数据预热完成: {total_records} 条记录")
        
        return {
            'total_funds': len(codes),
            'success': len([r for r in results if 'records' in r]),
            'failed': len([r for r in results if 'error' in r]),
            'total_records': total_records
        }
        
    def get_cache_status(self, code: str) -> Dict[str, Any]:
        """获取缓存状态"""
        try:
            db = SessionLocal()
            try:
                # 查询记录数
                count = db.query(FundNavHistory).filter(
                    FundNavHistory.fund_code == code
                ).count()
                
                # 查询日期范围
                first = db.query(FundNavHistory).filter(
                    FundNavHistory.fund_code == code
                ).order_by(FundNavHistory.nav_date.asc()).first()
                
                last = db.query(FundNavHistory).filter(
                    FundNavHistory.fund_code == code
                ).order_by(FundNavHistory.nav_date.desc()).first()
                
                return {
                    'code': code,
                    'cached_records': count,
                    'date_range': {
                        'from': first.nav_date.isoformat() if first else None,
                        'to': last.nav_date.isoformat() if last else None
                    },
                    'is_updating': code in self._update_locks and self._update_locks[code].locked()
                }
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"获取缓存状态失败 {code}: {e}")
            return {'code': code, 'error': str(e)}


# 单例模式
history_service = HistoryService()
