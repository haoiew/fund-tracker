# -*- coding: utf-8 -*-
"""
持仓管理服务 - 单用户本地工具
"""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Tuple, Dict
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from app.models.portfolio import PortfolioRebalanceRecord, PortfolioTransaction, UserPortfolio
from app.models.fund import Fund
from app.schemas.portfolio import (
    PortfolioCreate, PortfolioUpdate, PortfolioResponse,
    PortfolioSummary, PortfolioProfitDetail, PortfolioProfitResponse,
    PortfolioTransactionCreate, PortfolioTransactionResponse,
    PortfolioImportConfirmItem, PortfolioImportConfirmRequest, PortfolioImportConfirmResponse,
    PortfolioImportPreviewRequest, PortfolioImportPreviewResponse, PortfolioImportPreviewItem,
    PortfolioRebalanceRecordResponse, PortfolioTransactionImportConfirmItem,
    PortfolioTransactionImportConfirmRequest, PortfolioTransactionImportConfirmResponse,
    PortfolioTransactionImportPreviewItem, PortfolioTransactionImportPreviewRequest,
    PortfolioTransactionImportPreviewResponse
)
from app.logger import get_logger

logger = get_logger("portfolio_service")


class PortfolioServiceError(Exception):
    pass


class PortfolioService:
    def create_portfolio(self, db: Session, portfolio: PortfolioCreate) -> UserPortfolio:
        fund_code = portfolio.fund_code
        fund_name = portfolio.fund_name
        if not fund_name:
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
            db.flush()
            self._upsert_snapshot_transaction(db, db_portfolio, source="manual")
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

    def _upsert_snapshot_transaction(self, db: Session, portfolio: UserPortfolio, source: str = "snapshot") -> PortfolioTransaction:
        """Map legacy position edits to a single snapshot transaction."""
        trade_date = portfolio.buy_date or date.today()
        txn = (
            db.query(PortfolioTransaction)
            .filter(
                PortfolioTransaction.portfolio_id == portfolio.id,
                PortfolioTransaction.transaction_type == "snapshot",
            )
            .first()
        )
        if txn is None:
            txn = PortfolioTransaction(portfolio_id=portfolio.id, fund_code=portfolio.fund_code)
            db.add(txn)

        txn.fund_code = portfolio.fund_code
        txn.transaction_type = "snapshot"
        txn.trade_date = trade_date
        txn.shares = portfolio.hold_shares or Decimal('0')
        txn.amount = portfolio.cost_amount or Decimal('0')
        txn.nav = portfolio.cost_nav
        txn.fee = Decimal('0')
        txn.source = source
        txn.remark = portfolio.remark
        return txn

    def _recalculate_portfolio_from_transactions(self, db: Session, portfolio: UserPortfolio) -> UserPortfolio:
        transactions = (
            db.query(PortfolioTransaction)
            .filter(PortfolioTransaction.portfolio_id == portfolio.id)
            .order_by(PortfolioTransaction.trade_date, PortfolioTransaction.id)
            .all()
        )

        total_shares = Decimal('0')
        total_cost = Decimal('0')
        first_trade_date = None

        for txn in transactions:
            txn_type = txn.transaction_type
            shares = self._safe_decimal(txn.shares)
            amount = self._safe_decimal(txn.amount)
            fee = self._safe_decimal(txn.fee)
            if first_trade_date is None:
                first_trade_date = txn.trade_date

            if txn_type == "snapshot":
                total_shares = shares
                total_cost = amount
            elif txn_type == "buy":
                total_shares += shares
                total_cost += amount + fee
            elif txn_type == "sell":
                if shares > total_shares:
                    raise PortfolioServiceError("卖出份额不能超过当前持有份额")
                avg_cost = (total_cost / total_shares) if total_shares > 0 else Decimal('0')
                total_shares -= shares
                total_cost -= avg_cost * shares
                if total_shares == 0:
                    total_cost = Decimal('0')
            elif txn_type == "dividend":
                total_cost = max(Decimal('0'), total_cost - amount)

        portfolio.hold_shares = self._quantize(total_shares, "0.0001")
        portfolio.cost_amount = self._quantize(total_cost, "0.01")
        portfolio.cost_nav = self._quantize(total_cost / total_shares, "0.0001") if total_shares > 0 else None
        portfolio.buy_date = first_trade_date
        return portfolio

    def create_transaction(self, db: Session, transaction: PortfolioTransactionCreate) -> PortfolioTransaction:
        try:
            portfolio = self._resolve_transaction_portfolio(db, transaction)
            txn = PortfolioTransaction(
                portfolio_id=portfolio.id,
                fund_code=portfolio.fund_code,
                transaction_type=transaction.transaction_type,
                trade_date=transaction.trade_date,
                shares=transaction.shares,
                amount=transaction.amount,
                nav=transaction.nav,
                fee=transaction.fee,
                source=transaction.source,
                remark=transaction.remark,
            )
            db.add(txn)
            db.flush()
            self._recalculate_portfolio_from_transactions(db, portfolio)
            db.commit()
            db.refresh(txn)
            return txn
        except PortfolioServiceError:
            db.rollback()
            raise
        except SQLAlchemyError as e:
            db.rollback()
            raise PortfolioServiceError(f"交易流水保存失败: {str(e)}")

    def _resolve_transaction_portfolio(self, db: Session, transaction: PortfolioTransactionCreate) -> UserPortfolio:
        if transaction.portfolio_id is not None:
            portfolio = self.get_portfolio(db, transaction.portfolio_id)
            if not portfolio:
                raise PortfolioServiceError("持仓不存在")
            return portfolio

        assert transaction.fund_code is not None
        portfolio = (
            db.query(UserPortfolio)
            .filter(UserPortfolio.fund_code == transaction.fund_code)
            .order_by(UserPortfolio.id)
            .first()
        )
        if portfolio:
            return portfolio

        if transaction.transaction_type not in {"buy", "snapshot"}:
            raise PortfolioServiceError("只有买入或快照交易可以创建新持仓")

        try:
            from app.services.fund_service import get_fund_service
            fund_name = get_fund_service().get_fund_name(transaction.fund_code)
        except Exception:
            fund_name = transaction.fund_code

        self._get_or_create_fund(db, transaction.fund_code, fund_name)
        portfolio = UserPortfolio(
            fund_code=transaction.fund_code,
            hold_shares=Decimal('0'),
            cost_amount=Decimal('0'),
            cost_nav=None,
            buy_date=transaction.trade_date,
            remark=transaction.remark,
        )
        db.add(portfolio)
        db.flush()
        return portfolio

    def get_transactions(self, db: Session, portfolio_id: int) -> List[PortfolioTransaction]:
        return (
            db.query(PortfolioTransaction)
            .filter(PortfolioTransaction.portfolio_id == portfolio_id)
            .order_by(PortfolioTransaction.trade_date, PortfolioTransaction.id)
            .all()
        )

    def to_transaction_response(self, transaction: PortfolioTransaction) -> PortfolioTransactionResponse:
        return PortfolioTransactionResponse(
            id=transaction.id,
            portfolio_id=transaction.portfolio_id,
            fund_code=transaction.fund_code,
            fund_name=transaction.fund.name if transaction.fund else transaction.fund_code,
            transaction_type=transaction.transaction_type,
            trade_date=transaction.trade_date,
            shares=self._safe_decimal(transaction.shares),
            amount=self._safe_decimal(transaction.amount),
            nav=self._safe_decimal(transaction.nav) if transaction.nav is not None else None,
            fee=self._safe_decimal(transaction.fee),
            source=transaction.source or "manual",
            remark=transaction.remark,
            created_at=transaction.created_at,
            updated_at=transaction.updated_at,
        )

    def get_portfolio(self, db: Session, portfolio_id: int) -> Optional[UserPortfolio]:
        return (
            db.query(UserPortfolio)
            .options(joinedload(UserPortfolio.fund), joinedload(UserPortfolio.transactions))
            .filter(UserPortfolio.id == portfolio_id)
            .first()
        )

    def get_all_portfolios(self, db: Session) -> List[UserPortfolio]:
        return db.query(UserPortfolio).options(joinedload(UserPortfolio.fund), joinedload(UserPortfolio.transactions)).all()

    def update_portfolio(self, db: Session, portfolio_id: int, portfolio_update: PortfolioUpdate) -> Optional[UserPortfolio]:
        try:
            db_portfolio = self.get_portfolio(db, portfolio_id)
            if not db_portfolio:
                return None
            for field, value in portfolio_update.model_dump(exclude_unset=True).items():
                if field == "fund_name":
                    continue
                if field == "fund_code" and value:
                    self._get_or_create_fund(db, value, portfolio_update.fund_name or value)
                setattr(db_portfolio, field, value)
            db.flush()
            self._upsert_snapshot_transaction(db, db_portfolio, source="manual")
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
                db.flush()
                self._upsert_snapshot_transaction(db, db_portfolio, source="import")
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
                profit_amount=profit_amount, profit_rate=profit_rate,
                transaction_count=len(portfolio.transactions) if portfolio.transactions is not None else 0
            )
        except Exception as e:
            logger.error(f"转换持仓响应失败 {portfolio.id}: {e}")
            return PortfolioResponse(
                id=portfolio.id, fund_code=fund_code, fund_name=fund_name,
                hold_shares=self._safe_decimal(portfolio.hold_shares),
                cost_amount=self._safe_decimal(portfolio.cost_amount),
                cost_nav=self._safe_decimal(portfolio.cost_nav),
                buy_date=portfolio.buy_date, remark=portfolio.remark,
                created_at=portfolio.created_at, updated_at=portfolio.updated_at,
                transaction_count=len(portfolio.transactions) if portfolio.transactions is not None else 0
            )

    async def _fetch_import_realtime_map(self, codes: List[str]) -> Dict[str, object]:
        unique_codes: list[str] = []
        seen: set[str] = set()
        for code in codes:
            if code and code not in seen:
                unique_codes.append(code)
                seen.add(code)

        if not unique_codes:
            return {}

        try:
            from app.services.fund_service import get_fund_service
            rt_list = await get_fund_service().get_realtime_batch(unique_codes)
            return {code: rt for code, rt in zip(unique_codes, rt_list)}
        except Exception as e:
            logger.warning(f"导入预检批量获取实时净值失败: {e}")
            return {}

    async def preview_import(self, db: Session, request: PortfolioImportPreviewRequest) -> PortfolioImportPreviewResponse:
        existing_map = {p.fund_code: p for p in db.query(UserPortfolio).all()}
        existing_codes = set(existing_map.keys())
        seen_codes: set[str] = set()
        prepared_items = []
        realtime_codes: list[str] = []

        for holding in request.holdings:
            fund_code = holding.fund_code or ""
            warnings: list[str] = []
            status = "ready"
            reason = ""
            estimated_cost = holding.market_value - holding.holding_return

            if not fund_code:
                status = "skipped"
                reason = "缺少基金代码"
            elif request.strict and holding.match_status and holding.match_status != "matched":
                status = "skipped"
                reason = f"识别状态为 {holding.match_status}，需要人工确认"
            elif holding.confidence is not None and holding.confidence < 90:
                status = "skipped"
                reason = "基金匹配置信度低于90"
            elif fund_code in seen_codes:
                status = "skipped"
                reason = "导入数据中存在重复基金代码"
            elif request.mode == "append" and fund_code in existing_codes:
                status = "skipped"
                reason = "该基金已存在于当前持仓"
            elif estimated_cost <= 0:
                status = "invalid"
                reason = "市值减持有收益后成本不合理"
            elif holding.holding_return > holding.market_value * Decimal("0.8"):
                warnings.append("持有收益接近或超过市值，建议人工核对")

            if holding.holding_return < -holding.market_value * Decimal("10"):
                status = "invalid"
                reason = "亏损金额远超市值，疑似识别错误"

            if abs(holding.daily_return) > holding.market_value * Decimal("0.2"):
                warnings.append("昨日收益超过市值20%，建议核对数字识别")

            if holding.holding_return_rate is not None and estimated_cost > 0:
                implied_rate = holding.holding_return / estimated_cost * Decimal("100")
                if abs(implied_rate - holding.holding_return_rate) > Decimal("3"):
                    warnings.append("持有收益率与金额反推结果偏差较大")

            if fund_code:
                seen_codes.add(fund_code)
                realtime_codes.append(fund_code)

            prepared_items.append((holding, fund_code, status, reason, estimated_cost, warnings))

        rt_map = await self._fetch_import_realtime_map(realtime_codes)
        items: list[PortfolioImportPreviewItem] = []

        for holding, fund_code, status, reason, estimated_cost, warnings in prepared_items:
            current_nav = None
            current_change = None
            estimated_shares = None
            estimated_cost_nav = None
            fund_name = holding.fund_name

            rt = rt_map.get(fund_code) if fund_code else None
            if rt is not None:
                current_nav_value = self._safe_decimal(getattr(rt, "estimate_nav", None))
                current_change_value = getattr(rt, "estimate_change", None)
                current_nav = current_nav_value if current_nav_value > 0 else None
                current_change = self._safe_decimal(current_change_value) if current_change_value is not None else None
                rt_name = getattr(rt, "name", None)
                if rt_name and rt_name != fund_code and holding.match_status == "matched":
                    fund_name = rt_name

            if current_nav is not None and current_nav > 0 and estimated_cost > 0:
                raw_estimated_shares = holding.market_value / current_nav
                estimated_shares = self._quantize(raw_estimated_shares, "0.0001")
                if raw_estimated_shares > 0:
                    estimated_cost_nav = self._quantize(estimated_cost / raw_estimated_shares, "0.0001")

            if status == "ready":
                if current_nav is None or current_nav <= 0:
                    status = "invalid"
                    reason = "无法获取有效当前净值，不能反推份额"
                elif estimated_shares is None or estimated_shares <= 0 or estimated_cost_nav is None:
                    status = "invalid"
                    reason = "份额或成本净值反推失败"

            existing = existing_map.get(fund_code) if fund_code else None
            diff = self._build_import_diff(existing, holding.market_value, estimated_cost, estimated_shares)
            if request.mode == "rebalance" and existing is not None and status == "ready":
                if diff["diff_type"] == "unchanged":
                    status = "skipped"
                    reason = "与当前持仓基本一致，无需记录调仓"
                elif diff["confidence_score"] < 60:
                    status = "skipped"
                    reason = "推断置信度偏低，需要人工核对"

            items.append(PortfolioImportPreviewItem(
                row_index=holding.row_index,
                fund_code=fund_code,
                fund_name=fund_name,
                raw_fund_name=holding.raw_fund_name,
                market_value=holding.market_value,
                daily_return=holding.daily_return,
                holding_return=holding.holding_return,
                holding_return_rate=holding.holding_return_rate,
                estimated_cost=self._quantize(estimated_cost, "0.01"),
                current_nav=current_nav,
                current_change=current_change,
                estimated_shares=estimated_shares,
                estimated_cost_nav=estimated_cost_nav,
                match_status=holding.match_status,
                confidence=holding.confidence,
                status=status,
                reason=reason,
                warnings=warnings,
                diff_type=diff["diff_type"],
                existing_portfolio_id=existing.id if existing is not None else None,
                existing_shares=self._safe_decimal(existing.hold_shares) if existing is not None else None,
                existing_cost=self._safe_decimal(existing.cost_amount) if existing is not None else None,
                inferred_amount=diff["inferred_amount"],
                inferred_shares=diff["inferred_shares"],
                confidence_score=diff["confidence_score"],
            ))

        if request.mode == "rebalance":
            imported_codes = {item.fund_code for item in items if item.fund_code}
            for fund_code, existing in existing_map.items():
                if fund_code in imported_codes:
                    continue
                items.append(PortfolioImportPreviewItem(
                    fund_code=fund_code,
                    fund_name=existing.fund.name if existing.fund else fund_code,
                    market_value=Decimal('0'),
                    daily_return=Decimal('0'),
                    holding_return=Decimal('0'),
                    estimated_cost=Decimal('0'),
                    current_nav=None,
                    estimated_shares=Decimal('0'),
                    estimated_cost_nav=None,
                    match_status="matched",
                    confidence=100,
                    status="ready",
                    reason="当前截图中未出现，按清仓处理",
                    warnings=["推断为清仓，请确认截图是否包含完整持仓列表"],
                    diff_type="remove",
                    existing_portfolio_id=existing.id,
                    existing_shares=self._safe_decimal(existing.hold_shares),
                    existing_cost=self._safe_decimal(existing.cost_amount),
                    inferred_amount=-self._safe_decimal(existing.cost_amount),
                    inferred_shares=-self._safe_decimal(existing.hold_shares),
                    confidence_score=75,
                ))

        return PortfolioImportPreviewResponse(
            items=items,
            ready_count=sum(1 for item in items if item.status == "ready"),
            skipped_count=sum(1 for item in items if item.status == "skipped"),
            invalid_count=sum(1 for item in items if item.status == "invalid"),
        )

    def _build_import_diff(
        self,
        existing: Optional[UserPortfolio],
        market_value: Decimal,
        estimated_cost: Decimal,
        estimated_shares: Optional[Decimal],
    ) -> dict:
        after_shares = self._safe_decimal(estimated_shares)
        after_cost = self._safe_decimal(estimated_cost)
        if existing is None:
            return {
                "diff_type": "new",
                "inferred_amount": self._quantize(after_cost, "0.01"),
                "inferred_shares": self._quantize(after_shares, "0.0001"),
                "confidence_score": 80,
            }

        before_shares = self._safe_decimal(existing.hold_shares)
        before_cost = self._safe_decimal(existing.cost_amount)
        share_delta = after_shares - before_shares
        cost_delta = after_cost - before_cost
        share_tolerance = max(before_shares * Decimal("0.005"), Decimal("0.0001"))
        cost_tolerance = max(before_cost * Decimal("0.01"), Decimal("1.00"))

        if abs(share_delta) <= share_tolerance and abs(cost_delta) <= cost_tolerance:
            diff_type = "unchanged"
            confidence = 95
        elif before_shares <= 0 and after_shares > 0:
            diff_type = "new"
            confidence = 80
        elif after_shares <= 0:
            diff_type = "remove"
            confidence = 75
        elif share_delta > share_tolerance:
            diff_type = "increase"
            confidence = 85
        elif share_delta < -share_tolerance:
            diff_type = "decrease"
            confidence = 85
        else:
            diff_type = "adjust"
            confidence = 65

        if market_value <= 0 and diff_type != "remove":
            confidence = min(confidence, 50)

        return {
            "diff_type": diff_type,
            "inferred_amount": self._quantize(cost_delta, "0.01"),
            "inferred_shares": self._quantize(share_delta, "0.0001"),
            "confidence_score": confidence,
        }

    async def confirm_import(self, db: Session, request: PortfolioImportConfirmRequest) -> PortfolioImportConfirmResponse:
        preview = await self.preview_import(
            db,
            PortfolioImportPreviewRequest(holdings=request.holdings, strict=request.strict, mode=request.mode)
        )
        trade_date = request.trade_date or date.today()
        existing_codes = {code for (code,) in db.query(UserPortfolio.fund_code).all()}
        results: list[PortfolioImportConfirmItem] = []
        success_count = 0
        skipped_count = 0
        failed_count = 0

        try:
            for item in preview.items:
                if item.status != "ready":
                    skipped_count += 1
                    results.append(PortfolioImportConfirmItem(
                        row_index=item.row_index,
                        fund_code=item.fund_code,
                        fund_name=item.fund_name,
                        status="skipped",
                        error=item.reason or "预检未通过",
                    ))
                    continue
                if request.mode == "rebalance" and item.diff_type == "remove":
                    continue

                if request.mode == "append" and item.fund_code in existing_codes:
                    skipped_count += 1
                    results.append(PortfolioImportConfirmItem(
                        row_index=item.row_index,
                        fund_code=item.fund_code,
                        fund_name=item.fund_name,
                        status="skipped",
                        error="该基金已存在于当前持仓",
                    ))
                    continue

                hold_shares = self._safe_decimal(item.estimated_shares)
                cost_amount = self._safe_decimal(item.estimated_cost)
                cost_nav = self._safe_decimal(item.estimated_cost_nav)
                if hold_shares <= 0 or cost_amount <= 0 or cost_nav <= 0:
                    skipped_count += 1
                    results.append(PortfolioImportConfirmItem(
                        row_index=item.row_index,
                        fund_code=item.fund_code,
                        fund_name=item.fund_name,
                        status="skipped",
                        error="份额或成本数据不完整",
                    ))
                    continue

                savepoint = db.begin_nested()
                try:
                    self._get_or_create_fund(db, item.fund_code, item.fund_name)
                    db_portfolio = (
                        db.query(UserPortfolio)
                        .filter(UserPortfolio.fund_code == item.fund_code)
                        .order_by(UserPortfolio.id)
                        .first()
                    )
                    existing_before = None
                    if db_portfolio is not None:
                        existing_before = {
                            "shares": self._safe_decimal(db_portfolio.hold_shares),
                            "cost": self._safe_decimal(db_portfolio.cost_amount),
                            "market_value": self._safe_decimal(db_portfolio.hold_shares) * self._safe_decimal(item.current_nav),
                        }
                        db_portfolio.hold_shares = hold_shares
                        db_portfolio.cost_amount = cost_amount
                        db_portfolio.cost_nav = cost_nav
                        db_portfolio.buy_date = db_portfolio.buy_date or trade_date
                        db_portfolio.remark = "持仓截图覆盖" if request.mode == "overwrite" else "持仓截图推断调仓"
                    else:
                        db_portfolio = UserPortfolio(
                            fund_code=item.fund_code,
                            hold_shares=hold_shares,
                            cost_amount=cost_amount,
                            cost_nav=cost_nav,
                            buy_date=trade_date,
                            remark="持仓截图导入",
                        )
                        db.add(db_portfolio)
                    db.flush()
                    self._upsert_snapshot_transaction(db, db_portfolio, source="import")
                    if request.mode == "rebalance":
                        before = existing_before or {"shares": Decimal('0'), "cost": Decimal('0'), "market_value": Decimal('0')}
                        self._create_rebalance_record_from_preview(
                            db=db,
                            item=item,
                            trade_date=trade_date,
                            before_shares=before["shares"],
                            before_cost=before["cost"],
                            before_market_value=before["market_value"],
                        )
                    savepoint.commit()
                    existing_codes.add(item.fund_code)
                    success_count += 1
                    results.append(PortfolioImportConfirmItem(
                        row_index=item.row_index,
                        fund_code=item.fund_code,
                        fund_name=item.fund_name,
                        status="success",
                        portfolio_id=db_portfolio.id,
                    ))
                except Exception as e:
                    savepoint.rollback()
                    failed_count += 1
                    results.append(PortfolioImportConfirmItem(
                        row_index=item.row_index,
                        fund_code=item.fund_code,
                        fund_name=item.fund_name,
                        status="failed",
                        error=str(e),
                    ))

            if request.mode == "rebalance":
                for item in preview.items:
                    if item.status != "ready" or item.diff_type != "remove" or not item.existing_portfolio_id:
                        continue
                    portfolio = self.get_portfolio(db, item.existing_portfolio_id)
                    if portfolio is None:
                        continue
                    savepoint = db.begin_nested()
                    try:
                        before_shares = self._safe_decimal(portfolio.hold_shares)
                        before_cost = self._safe_decimal(portfolio.cost_amount)
                        before_market_value = before_cost
                        self._create_rebalance_record_from_preview(
                            db=db,
                            item=item,
                            trade_date=trade_date,
                            before_shares=before_shares,
                            before_cost=before_cost,
                            before_market_value=before_market_value,
                        )
                        portfolio.hold_shares = Decimal('0')
                        portfolio.cost_amount = Decimal('0')
                        portfolio.cost_nav = None
                        portfolio.remark = "持仓截图推断清仓"
                        self._upsert_snapshot_transaction(db, portfolio, source="import")
                        savepoint.commit()
                        success_count += 1
                        results.append(PortfolioImportConfirmItem(
                            row_index=item.row_index,
                            fund_code=item.fund_code,
                            fund_name=item.fund_name,
                            status="success",
                            portfolio_id=portfolio.id,
                        ))
                    except Exception as e:
                        savepoint.rollback()
                        failed_count += 1
                        results.append(PortfolioImportConfirmItem(
                            row_index=item.row_index,
                            fund_code=item.fund_code,
                            fund_name=item.fund_name,
                            status="failed",
                            error=str(e),
                        ))

            if success_count > 0:
                db.commit()
        except SQLAlchemyError as e:
            db.rollback()
            raise PortfolioServiceError(f"批量导入失败: {str(e)}")

        return PortfolioImportConfirmResponse(
            items=results,
            success_count=success_count,
            skipped_count=skipped_count,
            failed_count=failed_count,
        )

    def _create_rebalance_record_from_preview(
        self,
        *,
        db: Session,
        item: PortfolioImportPreviewItem,
        trade_date: date,
        before_shares: Decimal,
        before_cost: Decimal,
        before_market_value: Decimal,
    ) -> PortfolioRebalanceRecord:
        action_type = item.diff_type or "adjust"
        record = PortfolioRebalanceRecord(
            fund_code=item.fund_code,
            fund_name=item.fund_name,
            action_type=action_type,
            trade_date=trade_date,
            before_shares=self._quantize(before_shares, "0.0001"),
            after_shares=self._quantize(self._safe_decimal(item.estimated_shares), "0.0001"),
            before_cost_amount=self._quantize(before_cost, "0.01"),
            after_cost_amount=self._quantize(self._safe_decimal(item.estimated_cost), "0.01"),
            before_market_value=self._quantize(before_market_value, "0.01"),
            after_market_value=self._quantize(self._safe_decimal(item.market_value), "0.01"),
            inferred_shares=self._quantize(self._safe_decimal(item.inferred_shares), "0.0001"),
            inferred_amount=self._quantize(self._safe_decimal(item.inferred_amount), "0.01"),
            confidence=item.confidence_score or 0,
            source="ai_snapshot",
            remark=item.reason or "",
        )
        db.add(record)
        return record

    def get_rebalance_records(self, db: Session, limit: int = 200) -> List[PortfolioRebalanceRecord]:
        return (
            db.query(PortfolioRebalanceRecord)
            .order_by(PortfolioRebalanceRecord.trade_date.desc(), PortfolioRebalanceRecord.id.desc())
            .limit(limit)
            .all()
        )

    def to_rebalance_record_response(self, record: PortfolioRebalanceRecord) -> PortfolioRebalanceRecordResponse:
        return PortfolioRebalanceRecordResponse(
            id=record.id,
            fund_code=record.fund_code,
            fund_name=record.fund_name or (record.fund.name if record.fund else record.fund_code),
            action_type=record.action_type,
            trade_date=record.trade_date,
            before_shares=self._safe_decimal(record.before_shares),
            after_shares=self._safe_decimal(record.after_shares),
            before_cost_amount=self._safe_decimal(record.before_cost_amount),
            after_cost_amount=self._safe_decimal(record.after_cost_amount),
            before_market_value=self._safe_decimal(record.before_market_value),
            after_market_value=self._safe_decimal(record.after_market_value),
            inferred_shares=self._safe_decimal(record.inferred_shares),
            inferred_amount=self._safe_decimal(record.inferred_amount),
            confidence=record.confidence or 0,
            source=record.source or "ai_snapshot",
            remark=record.remark,
            created_at=record.created_at,
        )

    async def preview_transaction_import(
        self,
        db: Session,
        request: PortfolioTransactionImportPreviewRequest,
    ) -> PortfolioTransactionImportPreviewResponse:
        existing_map = {p.fund_code: p for p in db.query(UserPortfolio).all()}
        realtime_codes: list[str] = []
        prepared_items = []
        for txn in request.transactions:
            fund_code = txn.fund_code or ""
            status = "ready"
            reason = ""
            warnings: list[str] = []

            if not fund_code:
                status = "skipped"
                reason = "缺少基金代码"
            elif request.strict and txn.match_status and txn.match_status != "matched":
                status = "skipped"
                reason = f"识别状态为 {txn.match_status}，需要人工确认"
            elif txn.confidence is not None and txn.confidence < 90:
                status = "skipped"
                reason = "基金匹配置信度低于90"
            elif txn.transaction_type not in {"buy", "sell", "dividend"}:
                status = "invalid"
                reason = "交易明细截图只支持买入、卖出和分红流水"
            elif txn.order_status and "完成" not in txn.order_status and "成功" not in txn.order_status:
                warnings.append("订单状态不是明确完成，请核对后再导入")

            if txn.transaction_type == "sell" and fund_code and fund_code not in existing_map:
                status = "skipped"
                reason = "卖出交易需要已有持仓"

            if fund_code:
                realtime_codes.append(fund_code)
            prepared_items.append((txn, fund_code, status, reason, warnings))

        rt_map = await self._fetch_import_realtime_map(realtime_codes)
        items: list[PortfolioTransactionImportPreviewItem] = []
        for txn, fund_code, status, reason, warnings in prepared_items:
            current_nav = None
            estimated_shares = None
            rt = rt_map.get(fund_code) if fund_code else None
            if rt is not None:
                current_nav_value = self._safe_decimal(getattr(rt, "estimate_nav", None))
                current_nav = current_nav_value if current_nav_value > 0 else None
            if current_nav is not None and current_nav > 0:
                estimated_shares = self._quantize(txn.amount / current_nav, "0.0001")
            elif status == "ready" and txn.transaction_type in {"buy", "sell"}:
                status = "invalid"
                reason = "无法获取有效当前净值，不能反推交易份额"

            existing = existing_map.get(fund_code) if fund_code else None
            items.append(PortfolioTransactionImportPreviewItem(
                row_index=txn.row_index,
                fund_code=fund_code,
                fund_name=txn.fund_name,
                raw_fund_name=txn.raw_fund_name,
                transaction_type=txn.transaction_type,
                trade_date=txn.trade_date,
                trade_time=txn.trade_time,
                amount=txn.amount,
                order_status=txn.order_status,
                status=status,
                reason=reason,
                warnings=warnings,
                match_status=txn.match_status,
                confidence=txn.confidence,
                match_reason=txn.match_reason,
                current_nav=current_nav,
                estimated_shares=estimated_shares,
                existing_portfolio_id=existing.id if existing is not None else None,
            ))

        return PortfolioTransactionImportPreviewResponse(
            items=items,
            ready_count=sum(1 for item in items if item.status == "ready"),
            skipped_count=sum(1 for item in items if item.status == "skipped"),
            invalid_count=sum(1 for item in items if item.status == "invalid"),
        )

    async def confirm_transaction_import(
        self,
        db: Session,
        request: PortfolioTransactionImportConfirmRequest,
    ) -> PortfolioTransactionImportConfirmResponse:
        preview = await self.preview_transaction_import(
            db,
            PortfolioTransactionImportPreviewRequest(transactions=request.transactions, strict=request.strict),
        )
        results: list[PortfolioTransactionImportConfirmItem] = []
        success_count = 0
        skipped_count = 0
        failed_count = 0

        try:
            for item in preview.items:
                if item.status != "ready":
                    skipped_count += 1
                    results.append(PortfolioTransactionImportConfirmItem(
                        row_index=item.row_index,
                        fund_code=item.fund_code or "",
                        fund_name=item.fund_name,
                        status="skipped",
                        error=item.reason or "预检未通过",
                    ))
                    continue

                shares = self._safe_decimal(item.estimated_shares)
                amount = self._safe_decimal(item.amount)
                if item.transaction_type in {"buy", "sell"} and shares <= 0:
                    skipped_count += 1
                    results.append(PortfolioTransactionImportConfirmItem(
                        row_index=item.row_index,
                        fund_code=item.fund_code or "",
                        fund_name=item.fund_name,
                        status="skipped",
                        error="交易份额反推失败",
                    ))
                    continue

                savepoint = db.begin_nested()
                try:
                    self._get_or_create_fund(db, item.fund_code, item.fund_name)
                    transaction = PortfolioTransactionCreate(
                        fund_code=item.fund_code,
                        transaction_type=item.transaction_type,
                        trade_date=item.trade_date,
                        shares=shares if item.transaction_type in {"buy", "sell"} else Decimal('0'),
                        amount=amount,
                        nav=item.current_nav,
                        fee=Decimal('0'),
                        source="ai_txn",
                        remark=f"账户明细截图导入{f' {item.trade_time}' if item.trade_time else ''}",
                    )
                    portfolio = self._resolve_transaction_portfolio(db, transaction)
                    txn = PortfolioTransaction(
                        portfolio_id=portfolio.id,
                        fund_code=portfolio.fund_code,
                        transaction_type=transaction.transaction_type,
                        trade_date=transaction.trade_date,
                        shares=transaction.shares,
                        amount=transaction.amount,
                        nav=transaction.nav,
                        fee=transaction.fee,
                        source=transaction.source,
                        remark=transaction.remark,
                    )
                    db.add(txn)
                    db.flush()
                    self._recalculate_portfolio_from_transactions(db, portfolio)
                    savepoint.commit()
                    success_count += 1
                    results.append(PortfolioTransactionImportConfirmItem(
                        row_index=item.row_index,
                        fund_code=item.fund_code or "",
                        fund_name=item.fund_name,
                        status="success",
                        transaction_id=txn.id,
                        portfolio_id=portfolio.id,
                    ))
                except Exception as e:
                    savepoint.rollback()
                    failed_count += 1
                    results.append(PortfolioTransactionImportConfirmItem(
                        row_index=item.row_index,
                        fund_code=item.fund_code or "",
                        fund_name=item.fund_name,
                        status="failed",
                        error=str(e),
                    ))

            if success_count > 0:
                db.commit()
        except SQLAlchemyError as e:
            db.rollback()
            raise PortfolioServiceError(f"交易明细导入失败: {str(e)}")

        return PortfolioTransactionImportConfirmResponse(
            items=results,
            success_count=success_count,
            skipped_count=skipped_count,
            failed_count=failed_count,
        )

    @staticmethod
    def _safe_decimal(value) -> Decimal:
        try:
            return Decimal(str(value)) if value is not None else Decimal('0')
        except (ValueError, TypeError):
            return Decimal('0')

    @staticmethod
    def _quantize(value: Decimal, places: str) -> Decimal:
        return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)


portfolio_service = PortfolioService()
