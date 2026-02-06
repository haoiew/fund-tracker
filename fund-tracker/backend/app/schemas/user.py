# -*- coding: utf-8 -*-
"""
用户相关Pydantic模型
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class UserBase(BaseModel):
    """用户基础模型"""
    username: Optional[str] = Field(None, max_length=50)
    avatar_url: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)


class UserCreate(UserBase):
    """创建用户"""
    openid: str = Field(..., description="微信openid")
    unionid: Optional[str] = Field(None, description="微信unionid")


class UserUpdate(UserBase):
    """更新用户"""
    default_up_days: Optional[int] = Field(None, ge=1, le=30)
    default_up_pct: Optional[Decimal] = Field(None, ge=0, le=1)
    default_down_days: Optional[int] = Field(None, ge=1, le=30)
    default_down_pct: Optional[Decimal] = Field(None, ge=0, le=1)


class UserResponse(UserBase):
    """用户响应模型"""
    id: int
    openid: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    
    # 用户设置
    default_up_days: int
    default_up_pct: Decimal
    default_down_days: int
    default_down_pct: Decimal
    
    class Config:
        from_attributes = True


class WechatLoginRequest(BaseModel):
    """微信登录请求"""
    code: str = Field(..., description="微信登录临时code")


class WechatLoginResponse(BaseModel):
    """微信登录响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class UserSettings(BaseModel):
    """用户设置"""
    default_up_days: int = Field(default=2, ge=1, le=30)
    default_up_pct: Decimal = Field(default=0.03, ge=0, le=1)
    default_down_days: int = Field(default=3, ge=1, le=30)
    default_down_pct: Decimal = Field(default=0.03, ge=0, le=1)
