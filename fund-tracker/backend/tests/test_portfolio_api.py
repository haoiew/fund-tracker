# -*- coding: utf-8 -*-
"""
持仓API测试程序
用于验证 /portfolio/summary 接口返回的数据结构
"""
import requests
import json

BASE_URL = "http://localhost:8001/api/v1"

def test_portfolio_summary():
    """测试持仓汇总接口"""
    print("=" * 60)
    print("测试 /portfolio/summary 接口")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/portfolio/summary", params={"user_id": 1})
        print(f"\n状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n完整响应:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            # 验证数据结构
            print("\n" + "-" * 60)
            print("数据结构验证:")
            print("-" * 60)
            
            if "data" not in data:
                print("❌ 错误: 响应中缺少 'data' 字段")
                return False
            
            inner_data = data["data"]
            
            # 检查 items
            if "items" not in inner_data:
                print("❌ 错误: data 中缺少 'items' 字段")
                return False
            
            items = inner_data["items"]
            print(f"✅ items 字段存在，类型: {type(items)}, 长度: {len(items)}")
            
            if not isinstance(items, list):
                print(f"❌ 错误: items 不是列表，而是 {type(items)}")
                return False
            
            # 检查 stats
            if "stats" not in inner_data:
                print("❌ 错误: data 中缺少 'stats' 字段")
                return False
            
            stats = inner_data["stats"]
            print(f"✅ stats 字段存在: {stats}")
            
            # 检查 stats 中的必要字段
            required_stats = ["total_cost", "total_value", "total_profit_loss", "total_profit_loss_pct", "item_count"]
            for field in required_stats:
                if field not in stats:
                    print(f"❌ 错误: stats 中缺少 '{field}' 字段")
                    return False
                print(f"✅ stats.{field} = {stats[field]}")
            
            # 检查 items 中的数据
            if len(items) > 0:
                print("\n" + "-" * 60)
                print(f"检查第一条数据:")
                print("-" * 60)
                first_item = items[0]
                required_fields = ["id", "fund_code", "fund_name", "hold_shares", "cost_nav", "current_nav"]
                for field in required_fields:
                    if field in first_item:
                        print(f"✅ {field}: {first_item[field]}")
                    else:
                        print(f"⚠️  {field}: 缺失")
            
            print("\n" + "=" * 60)
            print(f"✅ 测试通过! 共 {len(items)} 条持仓记录")
            print("=" * 60)
            return True
        else:
            print(f"❌ 请求失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 测试出错: {e}")
        return False

def test_portfolio_list():
    """测试持仓列表接口"""
    print("\n" + "=" * 60)
    print("测试 /portfolio (列表) 接口")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/portfolio", params={"user_id": 1})
        print(f"\n状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n完整响应:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            if "data" in data and isinstance(data["data"], list):
                items = data["data"]
                print(f"\n✅ 获取到 {len(items)} 条持仓记录")
                return True
            else:
                print("❌ 响应格式不正确")
                return False
        else:
            print(f"❌ 请求失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 测试出错: {e}")
        return False

if __name__ == "__main__":
    print("\n开始测试持仓API...\n")
    
    result1 = test_portfolio_summary()
    result2 = test_portfolio_list()
    
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"/portfolio/summary: {'✅ 通过' if result1 else '❌ 失败'}")
    print(f"/portfolio: {'✅ 通过' if result2 else '❌ 失败'}")
    print("=" * 60)
