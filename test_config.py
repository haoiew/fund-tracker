# -*- coding: utf-8 -*-
"""
配置测试脚本
验证所有配置模块是否正常工作
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_shared_config():
    """测试统一配置模块"""
    print("=" * 60)
    print("测试统一配置模块 (shared/config.py)")
    print("=" * 60)
    
    # 设置 DEBUG 环境变量
    os.environ['DEBUG'] = 'true'
    
    try:
        from shared import (
            BaseConfig,
            FundConfig,
            ChartConfig,
            PlotConfig,
            OcrConfig,
            ServerConfig,
            get_fund_config,
            get_chart_config,
            get_plot_config,
            get_server_config,
            get_ocr_config,
            CONFIG,
            validate_config,
            ConfigLoader
        )
        print("✅ 成功导入统一配置模块")
        
        # 测试配置类
        print("\n测试配置类实例化...")
        fund_config = get_fund_config()
        chart_config = get_chart_config()
        plot_config = get_plot_config()
        server_config = get_server_config()
        ocr_config = get_ocr_config()
        
        print(f"✅ FundConfig: {len(fund_config.DEFAULT_FUNDS)} 只基金")
        print(f"✅ ChartConfig: {len(chart_config.TIME_RANGES)} 个时间范围")
        print(f"✅ PlotConfig: mode={plot_config.PLOT_MODE}, range={plot_config.PLOT_RANGE}")
        print(f"✅ ServerConfig: {server_config.HOST}:{server_config.PORT}")
        print(f"✅ OcrConfig: {ocr_config.OCR_LANG}")
        
        # 测试向后兼容的 CONFIG
        print("\n测试向后兼容的 CONFIG 字典...")
        print(f"✅ CONFIG 包含 {len(CONFIG)} 个配置项")
        print(f"   - file_path: {CONFIG['file_path']}")
        print(f"   - default_funds: {len(CONFIG['default_funds'])} 只")
        
        # 测试配置验证
        print("\n测试配置验证...")
        errors = validate_config(fund_config)
        if errors:
            print(f"❌ 配置验证失败: {'; '.join(errors)}")
            return False
        else:
            print("✅ 配置验证通过")
        
        # 测试配置重载
        print("\n测试配置重载...")
        ConfigLoader.reload()
        fund_config2 = get_fund_config()
        print("✅ 配置重载成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 统一配置模块测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fund_core():
    """测试 fund_core.py"""
    print("\n" + "=" * 60)
    print("测试 fund_core.py")
    print("=" * 60)
    
    try:
        import fund_core
        
        # 检查 CONFIG 是否存在
        if hasattr(fund_core, 'CONFIG'):
            print("✅ fund_core.CONFIG 存在")
            print(f"   - 包含 {len(fund_core.CONFIG)} 个配置项")
        else:
            print("❌ fund_core.CONFIG 不存在")
            return False
        
        # 检查核心类
        if hasattr(fund_core, 'FundTracker'):
            print("✅ FundTracker 类存在")
        else:
            print("❌ FundTracker 类不存在")
            return False
        
        if hasattr(fund_core, 'PlotManager'):
            print("✅ PlotManager 类存在")
        else:
            print("❌ PlotManager 类不存在")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ fund_core.py 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_backend_config():
    """测试后端配置"""
    print("\n" + "=" * 60)
    print("测试后端配置 (fund-tracker/backend/app/config.py)")
    print("=" * 60)
    
    # 设置 DEBUG 环境变量
    os.environ['DEBUG'] = 'true'
    
    backend_config_path = os.path.join(
        os.path.dirname(__file__),
        'fund-tracker', 'backend'
    )
    
    if not os.path.exists(backend_config_path):
        print("⚠️  后端目录不存在，跳过测试")
        return True
    
    sys.path.insert(0, backend_config_path)
    
    try:
        from app.config import (
            fund_config,
            chart_config,
            ocr_config,
            settings,
            USE_SHARED_CONFIG
        )
        
        print(f"✅ 成功导入后端配置")
        print(f"   - 使用共享配置: {USE_SHARED_CONFIG}")
        print(f"   - settings.HOST: {settings.HOST}")
        print(f"   - settings.PORT: {settings.PORT}")
        print(f"   - fund_config: {len(fund_config.DEFAULT_FUNDS)} 只基金")
        
        return True
        
    except Exception as e:
        print(f"❌ 后端配置测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n🧪 开始配置测试...\n")
    
    results = []
    
    # 测试统一配置模块
    results.append(("统一配置模块", test_shared_config()))
    
    # 测试 fund_core.py
    results.append(("fund_core.py", test_fund_core()))
    
    # 测试后端配置
    results.append(("后端配置", test_backend_config()))
    
    # 输出测试结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有测试通过！")
        return 0
    else:
        print("❌ 部分测试失败，请检查错误信息")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)