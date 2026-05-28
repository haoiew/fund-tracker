# -*- coding: utf-8 -*-
"""
持仓管理服务 - 单用户本地工具
"""
from decimal import Decimal
from typing import List, Optional, Tuple, Dict
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from app.models.portfolio import UserPortfolio
from app.models.fund import Fund
from app.schemas.portfolio import (
    PortfolioCreate, PortfolioUpdate, PortfolioResponse,
    PortfolioSummary, PortfolioProfitDetail, PortfolioProfitResponse
)
from app.logger import get_logger

logger = get_logger("portfolio_service")


class PortfolioServiceError(Exception):
    pass


class PortfolioService:
    def create_portfolio(self, db: Session, portfolio: PortfolioCreate) -> UserPortfolio:
        fund_code = portfolio.fund_code
        try:
            from app.services.fund_service import get_fund_service
            fund_name = get_fund_service().get_fund_name(fund_code)
        except Exception:
            fund_name = fund_code

        try:
            fund = self._get_or_create_fund(db, fund_code, fund_name)
            db_portfolio = UserPortfolio(
                fund_code=fund_code,
                hold_shares=portfolio.hold_shares,
                cost_amount=portfolio.cost_amount,
                cost_nav=portfolio.cost_nav,
                buy_date=portfolio.buy_date,
                remark=portfolio.remark
            )
            db.add(db_portfolio)
            db.commit()
            db.refresh(db_portfolio)
            return db_portfolio
        except IntegrityError:
            db.rollback()
            raise PortfolioServiceError("该基金已存在于持仓中")
        except SQLAlchemyError as e:
            db.rollback()
            raise PortfolioServiceError(f"数据库操作失败: {str(e)}")

    def _get_or_create_fund(self, db: Session, fund_code: str, fund_name: str) -> Fund:
        fund = db.query(Fund).filter(Fund.code == fund_code).first()
        if fund:
            return fund
        savepoint = db.begin_nested()
        try:
            fund = Fund(code=fund_code, name=fund_name)
            db.add(fund)
            savepoint.commit()
            db.flush()
            return fund
        except IntegrityError:
            savepoint.rollback()
            fund = db.query(Fund).filter(Fund.code == fund_code).first()
            if fund:
                return fund
            raise

    def get_portfolio(self, db: Session, portfolio_id: int) -> Optional[UserPortfolio]:
        return db.query(UserPortfolio).filter(UserPortfolio.id == portfolio_id).first()

    def get_all_portfolios(self, db: Session) -> List[UserPortfolio]:
        return db.query(UserPortfolio).options(joinedload(UserPortfolio.fund)).all()

    def update_portfolio(self, db: Session, portfolio_id: int, portfolio_update: PortfolioUpdate) -> Optional[UserPortfolio]:
        try:
            db_portfolio = self.get_portfolio(db, portfolio_id)
            if not db_portfolio:
                return None
            for field, value in portfolio_update.model_dump(exclude_unset=True).items():
                setattr(db_portfolio, field, value)
            db.commit()
            db.refresh(db_portfolio)
            return db_portfolio
        except SQLAlchemyError as e:
            db.rollback()
            raise PortfolioServiceError(f"更新失败: {str(e)}")

    def delete_portfolio(self, db: Session, portfolio_id: int) -> bool:
        try:
            db_portfolio = self.get_portfolio(db, portfolio_id)
            if not db_portfolio:
                return False
            db.delete(db_portfolio)
            db.commit()
            return True
        except SQLAlchemyError as e:
            db.rollback()
            raise PortfolioServiceError(f"删除失败: {str(e)}")

    def batch_create_portfolios(self, db: Session, portfolios: List[PortfolioCreate]) -> Tuple[List[UserPortfolio], List[str]]:
        success_list, error_list = [], []

        fund_codes = list(set(p.fund_code for p in portfolios))
        fund_names = {}
        from app.services.fund_service import get_fund_service
        fs = get_fund_service()
        for code in fund_codes:
            fund_names[code] = fs.get_fund_name(code)

        for portfolio in portfolios:
            savepoint = db.begin_nested()
            try:
                fund = self._get_or_create_fund(db, portfolio.fund_code, fund_names.get(portfolio.fund_code, portfolio.fund_code))
                db_portfolio = UserPortfolio(
                    fund_code=portfolio.fund_code,
                    hold_shares=portfolio.hold_shares,
                    cost_amount=portfolio.cost_amount,
                    cost_nav=portfolio.cost_nav,
                    buy_date=portfolio.buy_date,
                    remark=portfolio.remark
                )
                db.add(db_portfolio)
                savepoint.commit()
                success_list.append(db_portfolio)
            except IntegrityError:
                savepoint.rollback()
                error_list.append(f"{portfolio.fund_code}: 已存在")
            except Exception as e:
                savepoint.rollback()
                error_list.append(f"{portfolio.fund_code}: {str(e)}")

        if success_list:
            db.commit()
            for item in success_list:
                db.refresh(item)
        return success_list, error_list

    async def calculate_portfolio_profit(self, db: Session, rt_map: Optional[Dict] = None) -> PortfolioProfitResponse:
        portfolios = self.get_all_portfolios(db)
        if not portfolios:
            return PortfolioProfitResponse(
                summary=PortfolioSummary(total_cost=Decimal('0'), total_value=Decimal('0'),
                                        total_profit=Decimal('0'), total_profit_rate=Decimal('0'),
                                        fund_count=0, up_count=0, down_count=0),
                details=[]
            )

        if rt_map is None:
            from app.services.fund_service import get_fund_service
            fs = get_fund_service()
            codes = [p.fund_code for p in portfolios]
            rt_list = await fs.get_realtime_batch(codes)
            rt_map = {code: rt for code, rt in zip(codes, rt_list)}

        details = []
        total_cost = Decimal('0')
        total_value = Decimal('0')
        up_count = down_count = 0

        for p in portfolios:
            try:
                rt = rt_map.get(p.fund_code)
                if rt is None:
                    continue

                current_value = p.hold_shares * rt.estimate_nav if rt.estimate_nav and p.hold_shares else p.cost_amount
                profit_amount = current_value - p.cost_amount
                profit_rate = (profit_amount / p.cost_amount * 100) if p.cost_amount > 0 else Decimal('0')

                daily_profit = None
                if rt.estimate_change is not None and p.hold_shares and rt.estimate_nav:
                    prev_value = p.hold_shares * (rt.estimate_nav / (1 + rt.estimate_change / 100))
                    daily_profit = current_value - prev_value

                details.append(PortfolioProfitDetail(
                    fund_code=p.fund_code, fund_name=p.fund.name if p.fund else p.fund_code,
                    cost_amount=p.cost_amount, current_value=current_value,
                    profit_amount=profit_amount, profit_rate=profit_rate, daily_profit=daily_profit
                ))
                total_cost += p.cost_amount
                total_value += current_value
                if profit_rate > 0:
                    up_count += 1
                elif profit_rate < 0:
                    down_count += 1
            except Exception as e:
                logger.error(f"计算基金收益失败 {p.fund_code}: {e}")

        total_profit = total_value - total_cost
        total_profit_rate = (total_profit / total_cost * 100) if total_cost > 0 else Decimal('0')

        return PortfolioProfitResponse(
            summary=PortfolioSummary(total_cost=total_cost, total_value=total_value,
                                    total_profit=total_profit, total_profit_rate=total_profit_rate,
                                    fund_count=len(portfolios), up_count=up_count, down_count=down_count),
            details=details
        )

    async def to_response(self, portfolio: UserPortfolio, rt_data=None) -> PortfolioResponse:
        fund_code = portfolio.fund_code or ''
        fund_name = portfolio.fund.name if portfolio.fund and portfolio.fund.name else fund_code

        try:
            if rt_data is None:
                from app.services.fund_service import get_fund_service
                rt_data = await get_fund_service().get_realtime_data(portfolio.fund_code)

            hold_shares = self._safe_decimal(portfolio.hold_shares)
            cost_amount = self._safe_decimal(portfolio.cost_amount)
            cost_nav = self._safe_decimal(portfolio.cost_nav)
            estimate_nav = self._safe_decimal(rt_data.estimate_nav)

            if estimate_nav > 0 and hold_shares > 0:
                current_value = hold_shares * estimate_nav
            else:
                current_value = cost_amount if cost_amount > 0 else Decimal('0')

            profit_amount = current_value - cost_amount
            profit_rate = (profit_amount / cost_amount * 100) if cost_amount > 0 else Decimal('0')

            return PortfolioResponse(
                id=portfolio.id, fund_code=fund_code, fund_name=fund_name,
                hold_shares=hold_shares, cost_amount=cost_amount, cost_nav=cost_nav if cost_nav > 0 else None,
                buy_date=portfolio.buy_date, remark=portfolio.remark,
                created_at=portfolio.created_at, updated_at=portfolio.updated_at,
                current_nav=estimate_nav if estimate_nav > 0 else None,
                current_change=self._safe_decimal(rt_data.estimate_change),
                current_value=current_value if current_value > 0 else None,
                profit_amount=profit_amount, profit_rate=profit_rate
            )
        except Exception as e:
            logger.error(f"转换持仓响应失败 {portfolio.id}: {e}")
            return PortfolioResponse(
                id=portfolio.id, fund_code=fund_code, fund_name=fund_name,
                hold_shares=self._safe_decimal(portfolio.hold_shares),
                cost_amount=self._safe_decimal(portfolio.cost_amount),
                cost_nav=self._safe_decimal(portfolio.cost_nav),
                buy_date=portfolio.buy_date, remark=portfolio.remark,
                created_at=portfolio.created_at, updated_at=portfolio.updated_at
            )

    @staticmethod
    def _safe_decimal(value) -> Decimal:
        try:
            return Decimal(str(value)) if value is not None else Decimal('0')
        except (ValueError, TypeError):
            return Decimal('0')


portfolio_service = PortfolioService()
