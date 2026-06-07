# -*- coding: utf-8 -*-
"""
持仓数据模型 - 单用户本地工具，无user_id
"""
from sqlalchemy import Column, Integer, String, DateTime, Date, Numeric, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class UserPortfolio(Base):
    """持仓表"""
    __tablename__ = "user_portfolio"

    id = Column(Integer, primary_key=True, index=True)
    fund_code = Column(String(10), ForeignKey("funds.code"), nullable=False, index=True)

    hold_shares = Column(Numeric(12, 4), default=0, comment="持有份额")
    cost_amount = Column(Numeric(12, 2), default=0, comment="投入金额")
    cost_nav = Column(Numeric(10, 4), comment="成本净值")
    buy_date = Column(Date, comment="购买日期")
    remark = Column(Text, comment="备注")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")

    fund = relationship("Fund", back_populates="portfolios")
    transactions = relationship(
        "PortfolioTransaction",
        back_populates="portfolio",
        cascade="all, delete-orphan",
        order_by="PortfolioTransaction.trade_date, PortfolioTransaction.id",
    )

    def __repr__(self):
        return f"<UserPortfolio(fund_code='{self.fund_code}')>"


class PortfolioTransaction(Base):
    """交易流水表，持仓由流水派生，旧持仓编辑会映射为快照流水。"""
    __tablename__ = "portfolio_transactions"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("user_portfolio.id", ondelete="CASCADE"), nullable=False, index=True)
    fund_code = Column(String(10), ForeignKey("funds.code"), nullable=False, index=True)

    transaction_type = Column(String(20), nullable=False, comment="buy/sell/dividend/snapshot")
    trade_date = Column(Date, nullable=False, comment="交易日期")
    shares = Column(Numeric(12, 4), default=0, comment="交易份额")
    amount = Column(Numeric(12, 2), default=0, comment="交易金额")
    nav = Column(Numeric(10, 4), comment="交易净值")
    fee = Column(Numeric(12, 2), default=0, comment="手续费")
    source = Column(String(20), default="manual", comment="manual/import/snapshot")
    remark = Column(Text, comment="备注")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")

    portfolio = relationship("UserPortfolio", back_populates="transactions")
    fund = relationship("Fund")

    __table_args__ = (
        Index("ix_portfolio_txn_portfolio_date", "portfolio_id", "trade_date"),
        Index("ix_portfolio_txn_fund_date", "fund_code", "trade_date"),
    )

    def __repr__(self):
        return f"<PortfolioTransaction(fund_code='{self.fund_code}', type='{self.transaction_type}')>"
