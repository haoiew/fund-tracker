# -*- coding: utf-8 -*-
"""
数据源测试主运行脚本
运行所有测试并生成JSON结果
"""
import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / '.env')


def load_fund_codes():
    """加载基金代码"""
    funds_file = Path(__file__).parent / 'funds.txt'
    with open(funds_file, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]


def run_single_source_test(source, fund_codes):
    """运行单个数据源的完整测试"""
    print(f"\n{'='*60}")
    print(f"测试数据源: {source.get_name()}")
    print(f"{'='*60}")

    result = {
        "name": source.get_name(),
        "feasibility": {},
        "stability": {},
        "accuracy": {},
        "timeliness": {},
        "performance": {}
    }

    # 1. 可行性测试
    print("\n[1/5] 可行性测试...")
    start = time.time()
    results = source.fetch_batch(fund_codes)
    total_ms = (time.time() - start) * 1000

    success_count = sum(1 for r in results if r.error is None)
    fail_count = len(fund_codes) - success_count
    success_rate = success_count / len(fund_codes)

    result["feasibility"] = {
        "total": len(fund_codes),
        "success": success_count,
        "fail": fail_count,
        "success_rate": round(success_rate, 4),
        "failed_funds": [r.code for r in results if r.error is not None][:10]
    }
    print(f"  成功率: {success_rate:.1%} ({success_count}/{len(fund_codes)})")

    # 2. 稳定性测试（3轮）
    print("\n[2/5] 稳定性测试...")
    rounds_results = []
    for i in range(3):
        round_results = source.fetch_batch(fund_codes)
        round_success = sum(1 for r in round_results if r.error is None)
        round_rate = round_success / len(fund_codes)
        round_avg_time = sum(r.fetch_duration_ms for r in round_results if r.fetch_duration_ms > 0) / max(1, sum(1 for r in round_results if r.fetch_duration_ms > 0))
        rounds_results.append({
            "round": i + 1,
            "success_rate": round_rate,
            "avg_time_ms": round_avg_time
        })
        if i < 2:
            time.sleep(5)

    import numpy as np
    success_rates = [r["success_rate"] for r in rounds_results]
    result["stability"] = {
        "rounds": 3,
        "success_rates": [round(r, 4) for r in success_rates],
        "mean_success_rate": round(float(np.mean(success_rates)), 4),
        "std_success_rate": round(float(np.std(success_rates)), 4),
        "mean_response_ms": round(float(np.mean([r["avg_time_ms"] for r in rounds_results])), 2)
    }
    print(f"  平均成功率: {np.mean(success_rates):.1%}")
    print(f"  成功率标准差: {np.std(success_rates):.2%}")

    # 3. 及时性测试
    print("\n[3/5] 及时性测试...")
    if results:
        valid_results = [r for r in results if r.error is None and r.update_time]
        if valid_results:
            from datetime import datetime, timedelta
            now = datetime.now()
            lags = []
            for r in valid_results[:5]:  # 检查前5只
                try:
                    # 尝试解析时间
                    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d']:
                        try:
                            update_dt = datetime.strptime(str(r.update_time).strip(), fmt)
                            lag_minutes = (now - update_dt).total_seconds() / 60
                            lags.append(lag_minutes)
                            break
                        except ValueError:
                            continue
                except:
                    pass

            if lags:
                result["timeliness"] = {
                    "avg_lag_minutes": round(float(np.mean(lags)), 2),
                    "max_lag_minutes": round(float(np.max(lags)), 2),
                    "min_lag_minutes": round(float(np.min(lags)), 2)
                }
                print(f"  平均延迟: {np.mean(lags):.1f}分钟")
            else:
                result["timeliness"] = {"note": "无法解析更新时间"}
        else:
            result["timeliness"] = {"note": "无有效数据"}

    # 4. 性能测试
    print("\n[4/5] 性能测试...")
    durations = [r.fetch_duration_ms for r in results if r.fetch_duration_ms > 0]
    if durations:
        result["performance"] = {
            "batch_total_ms": round(total_ms, 2),
            "single_avg_ms": round(float(np.mean(durations)), 2),
            "single_max_ms": round(float(np.max(durations)), 2),
            "single_min_ms": round(float(np.min(durations)), 2)
        }
        print(f"  批量总耗时: {total_ms:.0f}ms")
        print(f"  单次平均: {np.mean(durations):.0f}ms")

    # 5. 详细数据样本
    print("\n[5/5] 采集数据样本...")
    sample_results = []
    for r in results[:3]:  # 保存前3只基金的数据
        sample_results.append({
            "code": r.code,
            "name": r.name,
            "nav": r.nav,
            "change_pct": r.change_pct,
            "update_time": r.update_time,
            "error": r.error,
            "fetch_duration_ms": round(r.fetch_duration_ms, 2)
        })
    result["sample_data"] = sample_results

    return result


def main():
    """主函数"""
    print("=" * 60)
    print("基金数据源综合测试")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 加载基金代码
    fund_codes = load_fund_codes()
    print(f"\n基金数量: {len(fund_codes)}")
    print(f"基金代码: {', '.join(fund_codes[:5])}...")

    # 初始化数据源
    sources = []
    source_configs = [
        ("akshare", "AkshareSource", {}),
        ("efinance", "EfinanceSource", {}),
        # Tushare Pro 由于频率限制（1次/分钟），单独测试
        # ("tushare", "TushareSource", {"token": os.getenv('TUSHARE_TOKEN', '')}),
        ("eastmoney", "EastmoneyApiSource", {})
    ]

    # 检查是否要单独测试tushare
    test_tushare = os.getenv('TEST_TUSHARE', 'false').lower() == 'true'
    if test_tushare:
        token = os.getenv('TUSHARE_TOKEN', '')
        if token and token != 'your_token_here':
            source_configs.append(("tushare", "TushareSource", {"token": token}))

    for name, class_name, kwargs in source_configs:
        try:
            if name == "akshare":
                from sources.akshare_source import AkshareSource
                sources.append(AkshareSource())
            elif name == "efinance":
                from sources.efinance_source import EfinanceSource
                sources.append(EfinanceSource())
            elif name == "tushare":
                token = kwargs.get('token', '')
                if token and token != 'your_token_here':
                    from sources.tushare_source import TushareSource
                    sources.append(TushareSource(token))
                else:
                    print(f"  跳过 {name}: token未配置")
            elif name == "eastmoney":
                from sources.eastmoney_api_source import EastmoneyApiSource
                sources.append(EastmoneyApiSource())
            print(f"  加载数据源: {name}")
        except Exception as e:
            print(f"  跳过 {name}: {e}")

    # 运行测试
    all_results = {
        "run_id": datetime.now().strftime('%Y%m%d_%H%M%S'),
        "timestamp": datetime.now().isoformat(),
        "fund_codes": fund_codes,
        "fund_count": len(fund_codes),
        "sources": {}
    }

    for source in sources:
        try:
            result = run_single_source_test(source, fund_codes)
            all_results["sources"][source.get_name()] = result
        except Exception as e:
            print(f"\n{source.get_name()} 测试失败: {e}")
            all_results["sources"][source.get_name()] = {"error": str(e)}

    # 保存结果
    reports_dir = Path(__file__).parent / 'reports'
    reports_dir.mkdir(exist_ok=True)

    result_file = reports_dir / f"test_result_{all_results['run_id']}.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"测试完成！结果已保存到: {result_file}")
    print(f"{'='*60}")

    # 打印总结
    print("\n总结:")
    print("-" * 60)
    for name, data in all_results["sources"].items():
        if "error" in data:
            print(f"  {name}: 测试失败 - {data['error']}")
        else:
            feas = data.get("feasibility", {})
            print(f"  {name}: 成功率={feas.get('success_rate', 0):.1%}, "
                  f"稳定性={data.get('stability', {}).get('std_success_rate', 'N/A')}")

    return all_results


if __name__ == "__main__":
    main()
