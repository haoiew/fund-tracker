# -*- coding: utf-8 -*-
"""
基金数据模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Date, Numeric, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class Fund(Base):
    """基金基础信息表"""
    __tablename__ = "funds"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, nullable=False, index=True, comment="基金代码")
    name = Column(String(100), nullable=False, comment="基金名称")
    fund_type = Column(String(20), comment="基金类型")
    company = Column(String(100), comment="基金公司")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")

    nav_history = relationship("FundNavHistory", back_populates="fund", cascade="all, delete-orphan")
    portfolios = relationship("UserPortfolio", back_populates="fund")

    def __repr__(self):
        return f"<Fund(code='{self.code}', name='{self.name}')>"


class FundNavHistory(Base):
    """基金历史净值表"""
    __tablename__ = "fund_nav_history"

    id = Column(Integer, primary_key=True, index=True)
    fund_code = Column(String(10), ForeignKey("funds.code", ondelete="CASCADE"), nullable=False)
    nav_date = Column(Date, nullable=False, comment="净值日期")
    nav = Column(Numeric(10, 4), comment="单位净值")
    accum_nav = Column(Numeric(10, 4), comment="累计净值")
    daily_change = Column(Numeric(6, 2), comment="日涨跌幅(%)")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    fund = relationship("Fund", back_populates="nav_history")

    __table_args__ = (
        UniqueConstraint('fund_code', 'nav_date', name='uix_fund_nav_date'),
        Index('ix_fund_nav_code_date', 'fund_code', 'nav_date'),
        Index('ix_fund_nav_date', 'nav_date'),
    )

    def __repr__(self):
        return f"<FundNavHistory(code='{self.fund_code}', date='{self.nav_date}', nav={self.nav})>"
