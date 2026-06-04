# -*- coding: utf-8 -*-
"""
Pytest配置文件
定义共享fixtures和测试配置
"""
import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

# 加载环境变量
load_dotenv(Path(__file__).parent / '.env')


def load_fund_codes() -> list:
    """加载基金代码列表"""
    funds_file = Path(__file__).parent / 'funds.txt'
    if funds_file.exists():
        with open(funds_file, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    return []


@pytest.fixture(scope="session")
def fund_codes():
    """所有基金代码"""
    return load_fund_codes()


@pytest.fixture(scope="session")
def tushare_token():
    """Tushare token"""
    token = os.getenv('TUSHARE_TOKEN', '')
    if not token or token == 'your_token_here':
        pytest.skip("Tushare token未配置")
    return token


@pytest.fixture(scope="session")
def akshare_source():
    """AKShare数据源"""
    from sources.akshare_source import AkshareSource
    return AkshareSource()


@pytest.fixture(scope="session")
def efinance_source():
    """efinance数据源"""
    try:
        from sources.efinance_source import EfinanceSource
        return EfinanceSource()
    except ImportError:
        pytest.skip("efinance未安装")


@pytest.fixture(scope="session")
def tushare_source(tushare_token):
    """Tushare数据源"""
    from sources.tushare_source import TushareSource
    return TushareSource(tushare_token)


@pytest.fixture(scope="session")
def eastmoney_source():
    """自维护东方财富数据源"""
    from sources.eastmoney_api_source import EastmoneyApiSource
    return EastmoneyApiSource()


@pytest.fixture(scope="session")
def all_sources(akshare_source, efinance_source, tushare_source, eastmoney_source):
    """所有数据源"""
    return [akshare_source, efinance_source, tushare_source, eastmoney_source]
