# -*- coding: utf-8 -*-
"""
持仓管理服务 - 核心业务逻辑
"""
from decimal import Decimal
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.portfolio import UserPortfolio
from app.models.fund import Fund
from app.schemas.portfolio import (
    PortfolioCreate, PortfolioUpdate, PortfolioResponse,
    PortfolioSummary, PortfolioProfitDetail, PortfolioProfitResponse
)
from app.services.fund_service import fund_service


class PortfolioService:
    """持仓服务类"""
    
    def create_portfolio(self, db: Session, user_id: int, portfolio: PortfolioCreate) -> UserPortfolio:
        """创建持仓"""
        # 检查基金是否存在，不存在则创建
        fund = db.query(Fund).filter(Fund.code == portfolio.fund_code).first()
        if not fund:
            fund_name = fund_service.get_fund_name(portfolio.fund_code)
            fund = Fund(
                code=portfolio.fund_code,
                name=fund_name
            )
            db.add(fund)
            db.flush()
        
        # 创建持仓记录
        db_portfolio = UserPortfolio(
            user_id=user_id,
            fund_code=portfolio.fund_code,
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
    
    def get_portfolio(self, db: Session, portfolio_id: int, user_id: int) -> Optional[UserPortfolio]:
        """获取单个持仓"""
        return db.query(UserPortfolio).filter(
            UserPortfolio.id == portfolio_id,
            UserPortfolio.user_id == user_id
        ).first()
    
    def get_user_portfolios(self, db: Session, user_id: int) -> List[UserPortfolio]:
        """获取用户所有持仓"""
        return db.query(UserPortfolio).filter(
            UserPortfolio.user_id == user_id
        ).all()
    
    def update_portfolio(self, db: Session, portfolio_id: int, user_id: int, 
                        portfolio_update: PortfolioUpdate) -> Optional[UserPortfolio]:
        """更新持仓"""
        db_portfolio = self.get_portfolio(db, portfolio_id, user_id)
        if not db_portfolio:
            return None
        
        update_data = portfolio_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_portfolio, field, value)
        
        db.commit()
        db.refresh(db_portfolio)
        return db_portfolio
    
    def delete_portfolio(self, db: Session, portfolio_id: int, user_id: int) -> bool:
        """删除持仓"""
        db_portfolio = self.get_portfolio(db, portfolio_id, user_id)
        if not db_portfolio:
            return False
        
        db.delete(db_portfolio)
        db.commit()
        return True
    
    def calculate_portfolio_profit(self, db: Session, user_id: int) -> PortfolioProfitResponse:
        """计算持仓收益"""
        portfolios = self.get_user_portfolios(db, user_id)
        
        if not portfolios:
            return PortfolioProfitResponse(
                summary=PortfolioSummary(
                    total_cost=Decimal('0'),
                    total_value=Decimal('0'),
                    total_profit=Decimal('0'),
                    total_profit_rate=Decimal('0'),
                    fund_count=0,
                    up_count=0,
                    down_count=0
                ),
                details=[]
            )
        
        details = []
        total_cost = Decimal('0')
        total_value = Decimal('0')
        up_count = 0
        down_count = 0
        
        for p in portfolios:
            # 获取实时数据
            realtime = fund_service.get_realtime_data(p.fund_code)
            
            # 计算当前市值
            if realtime.estimate_nav and p.hold_shares:
                current_value = p.hold_shares * realtime.estimate_nav
            else:
                current_value = p.cost_amount
            
            # 计算盈亏
            profit_amount = current_value - p.cost_amount
            profit_rate = (profit_amount / p.cost_amount * 100) if p.cost_amount > 0 else Decimal('0')
            
            # 计算当日收益
            daily_profit = None
            if realtime.estimate_change is not None and p.hold_shares and realtime.estimate_nav:
                prev_value = p.hold_shares * (realtime.estimate_nav / (1 + realtime.estimate_change / 100))
                daily_profit = current_value - prev_value
            
            detail = PortfolioProfitDetail(
                fund_code=p.fund_code,
                fund_name=p.fund.name if p.fund else p.fund_code,
                cost_amount=p.cost_amount,
                current_value=current_value,
                profit_amount=profit_amount,
                profit_rate=profit_rate,
                daily_profit=daily_profit
            )
            details.append(detail)
            
            total_cost += p.cost_amount
            total_value += current_value
            
            if profit_rate > 0:
                up_count += 1
            elif profit_rate < 0:
                down_count += 1
        
        total_profit = total_value - total_cost
        total_profit_rate = (total_profit / total_cost * 100) if total_cost > 0 else Decimal('0')
        
        summary = PortfolioSummary(
            total_cost=total_cost,
            total_value=total_value,
            total_profit=total_profit,
            total_profit_rate=total_profit_rate,
            fund_count=len(portfolios),
            up_count=up_count,
            down_count=down_count
        )
        
        return PortfolioProfitResponse(summary=summary, details=details)
    
    def to_response(self, portfolio: UserPortfolio) -> PortfolioResponse:
        """转换为响应模型 - 统一使用与calculate_portfolio_profit相同的逻辑"""
        # 获取实时数据
        realtime = fund_service.get_realtime_data(portfolio.fund_code)

        # 转换数据类型，确保是数字
        try:
            hold_shares = float(portfolio.hold_shares) if portfolio.hold_shares else 0
        except (ValueError, TypeError):
            hold_shares = 0

        try:
            cost_amount = float(portfolio.cost_amount) if portfolio.cost_amount else 0
        except (ValueError, TypeError):
            cost_amount = 0

        cost_nav = float(portfolio.cost_nav) if portfolio.cost_nav else 0

        # realtime是Pydantic模型对象，使用属性访问
        estimate_nav = getattr(realtime, 'estimate_nav', None)
        estimate_change = getattr(realtime, 'estimate_change', None)

        # 转换estimate_nav为float
        try:
            estimate_nav_float = float(estimate_nav) if estimate_nav is not None else None
        except (ValueError, TypeError):
            estimate_nav_float = None

        # 统一计算逻辑：与calculate_portfolio_profit保持一致
        # 如果有实时净值且持有份额>0，使用实时净值计算；否则使用成本价
        if estimate_nav_float is not None and hold_shares > 0:
            current_nav = estimate_nav_float
            current_value = hold_shares * estimate_nav_float
        else:
            # fallback: 使用成本价作为当前净值
            current_nav = cost_nav if cost_nav > 0 else 0
            current_value = cost_amount if cost_amount > 0 else 0

        # 计算盈亏（与calculate_portfolio_profit一致）
        profit_amount = current_value - cost_amount
        profit_rate = (profit_amount / cost_amount * 100) if cost_amount > 0 else 0

        return PortfolioResponse(
            id=portfolio.id,
            user_id=portfolio.user_id,
            fund_code=portfolio.fund_code,
            fund_name=portfolio.fund.name if portfolio.fund else portfolio.fund_code,
            hold_shares=hold_shares,
            cost_amount=cost_amount,
            cost_nav=cost_nav if cost_nav > 0 else None,
            buy_date=portfolio.buy_date,
            remark=portfolio.remark,
            created_at=portfolio.created_at,
            updated_at=portfolio.updated_at,
            current_nav=current_nav if current_nav > 0 else None,
            current_change=float(estimate_change) if estimate_change is not None else None,
            current_value=current_value if current_value > 0 else None,
            profit_amount=profit_amount,
            profit_rate=profit_rate
        )


# 单例模式
portfolio_service = PortfolioService()
