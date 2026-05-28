# -*- coding: utf-8 -*-
"""
持仓数据模型 - 单用户本地工具，无user_id
"""
from sqlalchemy import Column, Integer, String, DateTime, Date, Numeric, ForeignKey, Text
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

    def __repr__(self):
        return f"<UserPortfolio(fund_code='{self.fund_code}')>"
