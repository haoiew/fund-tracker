# -*- coding: utf-8 -*-
"""
用户相关数据模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class User(Base):
    """用户表"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    openid = Column(String(50), unique=True, index=True, comment="微信openid")
    unionid = Column(String(50), comment="微信unionid")
    username = Column(String(50), comment="用户名")
    avatar_url = Column(String(255), comment="头像URL")
    phone = Column(String(20), comment="手机号")
    
    # 用户设置
    default_up_days = Column(Integer, default=2, comment="默认上涨天数阈值")
    default_up_pct = Column(Numeric(5, 4), default=0.03, comment="默认上涨幅度阈值")
    default_down_days = Column(Integer, default=3, comment="默认下跌天数阈值")
    default_down_pct = Column(Numeric(5, 4), default=0.03, comment="默认下跌幅度阈值")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")
    last_login = Column(DateTime(timezone=True), comment="最后登录时间")
    
    # 关联关系
    portfolios = relationship("UserPortfolio", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, openid='{self.openid}')>"
