# -*- coding: utf-8 -*-
"""
测试报告生成脚本
将JSON测试结果转换为Markdown报告
"""
import json
import sys
from pathlib import Path
from datetime import datetime


def load_latest_result():
    """加载最新的测试结果"""
    reports_dir = Path(__file__).parent / 'reports'
    result_files = sorted(reports_dir.glob('test_result_*.json'), reverse=True)
    if not result_files:
        print("未找到测试结果文件")
        sys.exit(1)
    with open(result_files[0], 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_markdown_report(data):
    """生成Markdown报告"""
    report = []
    report.append("# 基金数据源测试报告")
    report.append("")
    report.append(f"**测试时间**: {data.get('timestamp', 'N/A')}")
    report.append(f"**测试基金数量**: {data.get('fund_count', 'N/A')}")
    report.append(f"**基金代码**: {', '.join(data.get('fund_codes', [])[:10])}...")
    report.append("")

    # 执行摘要
    report.append("## 执行摘要")
    report.append("")
    sources = data.get('sources', {})
    for name, source_data in sources.items():
        if "error" in source_data:
            report.append(f"- **{name}**: 测试失败 - {source_data['error']}")
        else:
            feas = source_data.get('feasibility', {})
            stab = source_data.get('stability', {})
            perf = source_data.get('performance', {})
            report.append(f"- **{name}**: 成功率 {feas.get('success_rate', 0):.1%}, "
                         f"稳定性标准差 {stab.get('std_success_rate', 'N/A')}, "
                         f"批量耗时 {perf.get('batch_total_ms', 'N/A')}ms")
    report.append("")

    # 详细对比表
    report.append("## 详细对比")
    report.append("")
    report.append("| 数据源 | 成功率 | 成功数 | 失败数 | 稳定性(标准差) | 平均响应(ms) | 批量耗时(ms) |")
    report.append("|--------|--------|--------|--------|----------------|--------------|--------------|")

    for name, source_data in sources.items():
        if "error" not in source_data:
            feas = source_data.get('feasibility', {})
            stab = source_data.get('stability', {})
            perf = source_data.get('performance', {})
            report.append(f"| {name} | "
                         f"{feas.get('success_rate', 0):.1%} | "
                         f"{feas.get('success', 0)} | "
                         f"{feas.get('fail', 0)} | "
                         f"{stab.get('std_success_rate', 'N/A')} | "
                         f"{stab.get('mean_response_ms', 'N/A')} | "
                         f"{perf.get('batch_total_ms', 'N/A')} |")
    report.append("")

    # 各数据源详细分析
    report.append("## 各数据源详细分析")
    report.append("")

    for name, source_data in sources.items():
        if "error" in source_data:
            continue

        report.append(f"### {name}")
        report.append("")

        # 可行性
        feas = source_data.get('feasibility', {})
        report.append("**可行性测试**")
        report.append(f"- 总数: {feas.get('total', 0)}")
        report.append(f"- 成功: {feas.get('success', 0)}")
        report.append(f"- 失败: {feas.get('fail', 0)}")
        report.append(f"- 成功率: {feas.get('success_rate', 0):.1%}")
        if feas.get('failed_funds'):
            report.append(f"- 失败基金: {', '.join(feas['failed_funds'][:5])}")
        report.append("")

        # 稳定性
        stab = source_data.get('stability', {})
        report.append("**稳定性测试**")
        report.append(f"- 测试轮数: {stab.get('rounds', 0)}")
        report.append(f"- 平均成功率: {stab.get('mean_success_rate', 0):.1%}")
        report.append(f"- 成功率标准差: {stab.get('std_success_rate', 'N/A')}")
        report.append(f"- 平均响应时间: {stab.get('mean_response_ms', 'N/A')}ms")
        report.append("")

        # 及时性
        time_data = source_data.get('timeliness', {})
        report.append("**及时性测试**")
        if 'avg_lag_minutes' in time_data:
            report.append(f"- 平均延迟: {time_data['avg_lag_minutes']}分钟")
            report.append(f"- 最大延迟: {time_data['max_lag_minutes']}分钟")
        else:
            report.append(f"- {time_data.get('note', '无数据')}")
        report.append("")

        # 性能
        perf = source_data.get('performance', {})
        report.append("**性能测试**")
        report.append(f"- 批量总耗时: {perf.get('batch_total_ms', 'N/A')}ms")
        report.append(f"- 单次平均耗时: {perf.get('single_avg_ms', 'N/A')}ms")
        report.append(f"- 单次最大耗时: {perf.get('single_max_ms', 'N/A')}ms")
        report.append("")

        # 数据样本
        samples = source_data.get('sample_data', [])
        if samples:
            report.append("**数据样本**")
            report.append("")
            report.append("| 代码 | 名称 | 净值 | 涨跌幅 | 更新时间 |")
            report.append("|------|------|------|--------|----------|")
            for s in samples:
                report.append(f"| {s.get('code', '')} | "
                             f"{s.get('name', '')} | "
                             f"{s.get('nav', '')} | "
                             f"{s.get('change_pct', '')} | "
                             f"{s.get('update_time', '')} |")
            report.append("")

    # 结论和建议
    report.append("## 结论和建议")
    report.append("")

    # 分析最佳数据源
    best_source = None
    best_score = 0

    for name, source_data in sources.items():
        if "error" in source_data:
            continue

        feas = source_data.get('feasibility', {})
        stab = source_data.get('stability', {})
        perf = source_data.get('performance', {})

        # 综合评分
        score = feas.get('success_rate', 0) * 40  # 可行性权重40%
        score += (1 - min(stab.get('std_success_rate', 1), 1)) * 30  # 稳定性权重30%
        score += min(perf.get('single_avg_ms', 5000) / 1000, 1) * 30  # 性能权重30%

        if score > best_score:
            best_score = score
            best_source = name

    if best_source:
        report.append(f"### 推荐数据源: {best_source}")
        report.append("")
        report.append("基于综合评分，推荐使用该数据源作为主要数据源。")
        report.append("")

    report.append("### 数据源特性对比")
    report.append("")
    report.append("| 特性 | efinance | Tushare Pro | 自维护API | AKShare |")
    report.append("|------|----------|-------------|-----------|---------|")
    report.append("| 实时估值 | 有(封装东方财富) | 无(仅T+1) | 有(直接调用) | 部分(仅LOF) |")
    report.append("| 历史净值 | 有 | 有(结构化) | 有 | 有 |")
    report.append("| 数据新鲜度 | 实时 | T+1 | 实时 | T+1 |")
    report.append("| 维护成本 | 低 | 低 | 高 | 低 |")
    report.append("| 限流风险 | 中 | 低(积分制) | 高(无文档) | 低 |")
    report.append("| 可靠性 | 依赖上游 | 高(官方) | 脆弱 | 中 |")
    report.append("")

    report.append("### 建议")
    report.append("")
    report.append("1. **实时估值需求**: 推荐使用自维护API或efinance，它们支持实时数据")
    report.append("2. **历史数据需求**: 推荐使用Tushare Pro，数据结构化且可靠")
    report.append("3. **混合策略**: 建议采用多数据源降级策略，结合各数据源优势")
    report.append("")

    report.append("---")
    report.append(f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

    return '\n'.join(report)


def main():
    """主函数"""
    print("加载测试结果...")
    data = load_latest_result()

    print("生成Markdown报告...")
    report = generate_markdown_report(data)

    # 保存报告
    reports_dir = Path(__file__).parent / 'reports'
    report_file = reports_dir / 'DATA_SOURCE_COMPARISON_REPORT.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"报告已生成: {report_file}")


if __name__ == "__main__":
    main()
