# -*- coding: utf-8 -*-
"""
清空持仓和关注数据脚本
"""
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.base import SessionLocal, engine, Base
from app.models import UserPortfolio, Fund, FundNavHistory, FundRealtimeCache

def clear_portfolio_data():
    """清空持仓数据"""
    db = SessionLocal()
    try:
        # 清空持仓表
        portfolio_count = db.query(UserPortfolio).count()
        db.query(UserPortfolio).delete()
        print(f"✅ 已清空持仓表: {portfolio_count} 条记录")

        # 提交事务
        db.commit()
        print("✅ 数据库事务已提交")

    except Exception as e:
        db.rollback()
        print(f"❌ 清空数据失败: {e}")
        raise
    finally:
        db.close()

def clear_all_fund_data():
    """清空所有基金相关数据（包括历史数据）"""
    db = SessionLocal()
    try:
        # 清空持仓表
        portfolio_count = db.query(UserPortfolio).count()
        db.query(UserPortfolio).delete()
        print(f"✅ 已清空持仓表: {portfolio_count} 条记录")

        # 清空历史净值表
        history_count = db.query(FundNavHistory).count()
        db.query(FundNavHistory).delete()
        print(f"✅ 已清空历史净值表: {history_count} 条记录")

        # 清空实时缓存表
        cache_count = db.query(FundRealtimeCache).count()
        db.query(FundRealtimeCache).delete()
        print(f"✅ 已清空实时缓存表: {cache_count} 条记录")

        # 清空基金信息表
        fund_count = db.query(Fund).count()
        db.query(Fund).delete()
        print(f"✅ 已清空基金信息表: {fund_count} 条记录")

        # 提交事务
        db.commit()
        print("✅ 数据库事务已提交")

    except Exception as e:
        db.rollback()
        print(f"❌ 清空数据失败: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='清空基金跟踪器数据')
    parser.add_argument('--all', action='store_true', help='清空所有数据（包括历史数据）')
    args = parser.parse_args()

    print("=" * 50)
    print("🧹 开始清空数据...")
    print("=" * 50)

    if args.all:
        clear_all_fund_data()
    else:
        clear_portfolio_data()

    print("=" * 50)
    print("✅ 数据清空完成！")
    print("=" * 50)
    print("\n⚠️  请重启后端服务以生效！")
    print("   命令: python -m uvicorn app.main:app --reload --port 8001")
