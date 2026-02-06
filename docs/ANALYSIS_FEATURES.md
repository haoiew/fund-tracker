# 分析类功能详细设计文档

> 基于多数据源的投资分析功能设计
> 版本: v1.0.0
> 更新时间: 2026-02-06

---

## 目录

1. [基金相关性分析](#1-基金相关性分析)
2. [基金估值历史回溯](#2-基金估值历史回溯)
3. [智能定投建议](#3-智能定投建议)
4. [投资组合风险分析](#4-投资组合风险分析)
5. [市场情绪指数](#5-市场情绪指数)
6. [投资组合收益归因分析](#6-投资组合收益归因分析)

---

## 1. 基金相关性分析

### 1.1 功能概述

分析持仓基金之间的相关性，帮助投资者优化投资组合，降低风险集中度。

### 1.2 核心概念

**相关系数**: 衡量两只基金收益率之间的线性关系，范围 -1 到 1
- 1: 完全正相关（同涨同跌）
- 0: 无相关性
- -1: 完全负相关（此涨彼跌）

### 1.3 用户界面设计

```
┌─────────────────────────────────────────────────────────────┐
│                    基金相关性分析                            │
├─────────────────────────────────────────────────────────────┤
│  分析周期: [近1月 ▼]  [计算相关性]                          │
├─────────────────────────────────────────────────────────────┤
│                    相关性热力图                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │        │ 016531 │ 018125 │ 022365 │ 012709 │       │   │
│  │ 016531 │  1.00  │  0.75  │  0.82  │  0.45  │       │   │
│  │ 018125 │  0.75  │  1.00  │  0.68  │  0.52  │       │   │
│  │ 022365 │  0.82  │  0.68  │  1.00  │  0.38  │       │   │
│  │ 012709 │  0.45  │  0.52  │  0.38  │  1.00  │       │   │
│  └─────────────────────────────────────────────────────┘   │
│  图例: 🔴 高相关(>0.8)  🟡 中相关(0.5-0.8)  🟢 低相关(<0.5)│
├─────────────────────────────────────────────────────────────┤
│                    相关性分组                                │
│  📊 高相关组 (建议分散)                                      │
│     • 016531 - 022365 (相关性: 0.82)                        │
│                                                              │
│  📊 低相关推荐                                               │
│     • 012709 与组合平均相关性: 0.45 (分散效果好)             │
├─────────────────────────────────────────────────────────────┤
│                    风险提示                                  │
│  ⚠️ 发现 1 对高相关基金，建议考虑调整配置以降低风险集中度    │
└─────────────────────────────────────────────────────────────┘
```

### 1.4 后端设计

#### 数据模型

```python
# models/fund_correlation.py

from sqlalchemy import Column, Integer, String, Float, DateTime, Date
from app.db.base import Base

class FundCorrelation(Base):
    """基金相关性记录"""
    __tablename__ = "fund_correlations"
    
    id = Column(Integer, primary_key=True)
    fund_code_1 = Column(String(10), index=True)
    fund_code_2 = Column(String(10), index=True)
    correlation = Column(Float)  # 相关系数
    period_days = Column(Integer)  # 计算周期（天）
    calculation_date = Column(Date)
    updated_at = Column(DateTime)
```

#### 核心算法

```python
# services/correlation_analysis.py

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from scipy import stats

class CorrelationAnalysisService:
    """相关性分析服务"""
    
    async def calculate_correlation_matrix(
        self,
        fund_codes: List[str],
        period_days: int = 30
    ) -> Dict:
        """计算基金相关性矩阵"""
        
        # 1. 获取历史收益率数据
        returns_data = await self._get_historical_returns(fund_codes, period_days)
        
        # 2. 构建DataFrame
        df = pd.DataFrame(returns_data)
        
        # 3. 计算相关系数矩阵
        corr_matrix = df.corr(method='pearson')
        
        # 4. 转换为前端格式
        result = {
            'codes': fund_codes,
            'names': [await self._get_fund_name(c) for c in fund_codes],
            'matrix': corr_matrix.values.tolist(),
            'period_days': period_days
        }
        
        return result
    
    async def find_correlation_groups(
        self,
        fund_codes: List[str],
        threshold: float = 0.8
    ) -> List[Dict]:
        """找出高相关基金组"""
        corr_data = await self.calculate_correlation_matrix(fund_codes)
        matrix = np.array(corr_data['matrix'])
        codes = corr_data['codes']
        
        high_corr_pairs = []
        n = len(codes)
        
        for i in range(n):
            for j in range(i+1, n):
                if matrix[i][j] >= threshold:
                    high_corr_pairs.append({
                        'fund_1': codes[i],
                        'fund_2': codes[j],
                        'correlation': round(matrix[i][j], 2),
                        'name_1': await self._get_fund_name(codes[i]),
                        'name_2': await self._get_fund_name(codes[j])
                    })
        
        return high_corr_pairs
    
    async def get_diversification_suggestions(
        self,
        portfolio_codes: List[str]
    ) -> List[Dict]:
        """获取分散化建议"""
        # 获取所有可选基金
        all_funds = await self._get_all_available_funds()
        
        suggestions = []
        
        for fund in all_funds:
            if fund['code'] in portfolio_codes:
                continue
                
            # 计算该基金与现有组合的平均相关性
            avg_corr = await self._calculate_avg_correlation(
                fund['code'],
                portfolio_codes
            )
            
            if avg_corr < 0.5:  # 低相关
                suggestions.append({
                    'code': fund['code'],
                    'name': fund['name'],
                    'avg_correlation': round(avg_corr, 2),
                    'reason': '与现有组合相关性低，有助于分散风险'
                })
        
        # 按相关性排序
        suggestions.sort(key=lambda x: x['avg_correlation'])
        
        return suggestions[:5]  # 返回前5个建议
    
    async def _get_historical_returns(
        self,
        fund_codes: List[str],
        days: int
    ) -> Dict[str, List[float]]:
        """获取历史收益率数据"""
        returns_data = {}
        
        for code in fund_codes:
            # 从history_service获取历史净值
            history = await history_service.get_history(code, days)
            
            # 计算日收益率
            navs = [h['nav'] for h in history]
            returns = []
            for i in range(1, len(navs)):
                daily_return = (navs[i] - navs[i-1]) / navs[i-1]
                returns.append(daily_return)
            
            returns_data[code] = returns
        
        return returns_data
```

### 1.5 API端点

```python
# api/v1/analysis.py

from fastapi import APIRouter
from typing import List

router = APIRouter()

@router.post("/correlation/matrix")
async def get_correlation_matrix(
    fund_codes: List[str],
    period_days: int = 30
):
    """获取基金相关性矩阵"""
    service = CorrelationAnalysisService()
    return await service.calculate_correlation_matrix(fund_codes, period_days)

@router.post("/correlation/high-correlation")
async def get_high_correlation_pairs(
    fund_codes: List[str],
    threshold: float = 0.8
):
    """获取高相关基金对"""
    service = CorrelationAnalysisService()
    return await service.find_correlation_groups(fund_codes, threshold)

@router.post("/correlation/diversification-suggestions")
async def get_diversification_suggestions(
    portfolio_codes: List[str]
):
    """获取分散化建议"""
    service = CorrelationAnalysisService()
    return await service.get_diversification_suggestions(portfolio_codes)
```

---

## 2. 基金估值历史回溯

### 2.1 功能概述

追踪基金历史估值的准确率，评估各数据源的可靠性，帮助用户了解估值偏差情况。

### 2.2 用户界面设计

```
┌─────────────────────────────────────────────────────────────┐
│                    估值历史回溯                              │
├─────────────────────────────────────────────────────────────┤
│  基金: [016531 鹏华碳中和主题混合C ▼]  [近3月 ▼]          │
├─────────────────────────────────────────────────────────────┤
│                    准确率统计                                │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │   平均误差   │ │   最大误差   │ │   准确率    │           │
│  │   0.23%     │ │   1.15%     │ │   92.5%     │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
├─────────────────────────────────────────────────────────────┤
│                    估值 vs 实际净值趋势                      │
│  [双轴线图: 蓝色=估算净值, 红色=实际净值]                    │
├─────────────────────────────────────────────────────────────┤
│                    误差分布                                  │
│  [直方图: 误差分布情况]                                      │
├─────────────────────────────────────────────────────────────┤
│                    数据源准确率对比                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 数据源   │ 预测次数 │ 平均误差 │ 准确率 │ 可靠性   │   │
│  │ 天天基金 │   45    │  0.21%  │  94%   │ ⭐⭐⭐⭐⭐ │   │
│  │ 腾讯基金 │   45    │  0.28%  │  91%   │ ⭐⭐⭐⭐  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 后端设计

```python
# services/estimate_backtest.py

from datetime import datetime, timedelta
from typing import List, Dict
import statistics

class EstimateBacktestService:
    """估值回溯服务"""
    
    async def backtest_estimate_accuracy(
        self,
        fund_code: str,
        days: int = 90
    ) -> Dict:
        """回溯估值准确率"""
        
        # 1. 获取历史估值记录
        estimates = await self._get_estimate_history(fund_code, days)
        
        # 2. 获取实际净值
        actual_navs = await self._get_actual_nav_history(fund_code, days)
        
        # 3. 对比计算误差
        comparisons = []
        for est in estimates:
            date = est['date']
            if date in actual_navs:
                actual = actual_navs[date]
                estimate = est['nav']
                
                error = abs(estimate - actual)
                error_pct = (error / actual) * 100
                
                comparisons.append({
                    'date': date,
                    'estimate': estimate,
                    'actual': actual,
                    'error': error,
                    'error_pct': error_pct,
                    'data_source': est['source']
                })
        
        # 4. 计算统计指标
        if comparisons:
            errors = [c['error_pct'] for c in comparisons]
            stats = {
                'avg_error': round(statistics.mean(errors), 2),
                'max_error': round(max(errors), 2),
                'min_error': round(min(errors), 2),
                'std_error': round(statistics.stdev(errors), 2) if len(errors) > 1 else 0,
                'median_error': round(statistics.median(errors), 2),
                'accuracy': round(
                    sum(1 for e in errors if e < 0.5) / len(errors) * 100, 1
                )
            }
        else:
            stats = {}
        
        return {
            'fund_code': fund_code,
            'fund_name': await self._get_fund_name(fund_code),
            'period_days': days,
            'total_records': len(comparisons),
            'statistics': stats,
            'comparisons': comparisons[-30:]  # 最近30条明细
        }
    
    async def compare_source_accuracy(
        self,
        fund_code: str,
        days: int = 90
    ) -> List[Dict]:
        """对比各数据源的准确率"""
        estimates = await self._get_estimate_history(fund_code, days)
        actual_navs = await self._get_actual_nav_history(fund_code, days)
        
        source_stats = {}
        
        for est in estimates:
            source = est['source']
            date = est['date']
            
            if source not in source_stats:
                source_stats[source] = {'errors': [], 'count': 0}
            
            if date in actual_navs:
                error_pct = abs(est['nav'] - actual_navs[date]) / actual_navs[date] * 100
                source_stats[source]['errors'].append(error_pct)
                source_stats[source]['count'] += 1
        
        # 计算各数据源统计
        results = []
        for source, data in source_stats.items():
            if data['errors']:
                results.append({
                    'source': source,
                    'prediction_count': data['count'],
                    'avg_error': round(statistics.mean(data['errors']), 2),
                    'max_error': round(max(data['errors']), 2),
                    'accuracy': round(
                        sum(1 for e in data['errors'] if e < 0.5) / len(data['errors']) * 100, 1
                    ),
                    'reliability_score': self._calculate_reliability_score(data['errors'])
                })
        
        return sorted(results, key=lambda x: x['accuracy'], reverse=True)
    
    def _calculate_reliability_score(self, errors: List[float]) -> int:
        """计算可靠性评分"""
        avg_error = statistics.mean(errors)
        if avg_error < 0.2:
            return 5
        elif avg_error < 0.3:
            return 4
        elif avg_error < 0.5:
            return 3
        elif avg_error < 1.0:
            return 2
        else:
            return 1
```

---

## 3. 智能定投建议

### 3.1 功能概述

基于基金估值历史分位数、市场趋势等因素，智能推荐定投策略和金额。

### 3.2 定投策略类型

1. **估值定投**: 低估多投，高估少投/暂停
2. **均线定投**: 低于均线多投
3. **定期定额**: 传统定投
4. **智能加码**: 大跌时额外加仓

### 3.3 用户界面设计

```
┌─────────────────────────────────────────────────────────────┐
│                    智能定投建议                              │
├─────────────────────────────────────────────────────────────┤
│  选择基金: [016531 鹏华碳中和主题混合C ▼]                   │
│  基础定投金额: [¥1000] / 月                                 │
├─────────────────────────────────────────────────────────────┤
│                    当前估值分析                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 当前估值分位数: 35% (中等偏低)                        │   │
│  │ 近1年估值区间: 1.05 - 1.45                           │   │
│  │ 当前估值: 1.23                                       │   │
│  │ [==========|----------] 35%                          │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                    定投建议                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 💡 建议策略: 估值定投                                 │   │
│  │                                                      │   │
│  │ 本月建议定投: ¥1,500 (基础金额 × 1.5倍)              │   │
│  │ 理由: 当前估值处于近1年35%分位，建议适当增加定投金额   │   │
│  │                                                      │   │
│  │ 下次定投日期: 2026-02-15                            │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                    策略回测                                  │
│  [折线图: 不同定投策略的历史收益对比]                        │
│  定期定额: +15.2%  估值定投: +18.5%  智能加码: +21.3%       │
├─────────────────────────────────────────────────────────────┤
│              [生成定投计划]  [查看历史建议]                  │
└─────────────────────────────────────────────────────────────┘
```

### 3.4 后端设计

```python
# services/smart_invest.py

from datetime import datetime, timedelta
from typing import Dict, List
import statistics

class SmartInvestService:
    """智能定投服务"""
    
    async def get_invest_suggestion(
        self,
        fund_code: str,
        base_amount: float,
        strategy: str = "valuation"
    ) -> Dict:
        """获取定投建议"""
        
        # 1. 获取估值分位数
        percentile = await self._calculate_valuation_percentile(fund_code)
        
        # 2. 根据策略计算建议金额
        if strategy == "valuation":
            suggestion = self._valuation_based_suggestion(base_amount, percentile)
        elif strategy == "ma":
            suggestion = await self._ma_based_suggestion(fund_code, base_amount)
        elif strategy == "smart_add":
            suggestion = await self._smart_add_suggestion(fund_code, base_amount)
        else:
            suggestion = {"amount": base_amount, "multiplier": 1.0}
        
        # 3. 生成理由
        reason = self._generate_suggestion_reason(percentile, suggestion['multiplier'])
        
        return {
            'fund_code': fund_code,
            'fund_name': await self._get_fund_name(fund_code),
            'base_amount': base_amount,
            'suggested_amount': suggestion['amount'],
            'multiplier': suggestion['multiplier'],
            'strategy': strategy,
            'valuation_percentile': percentile,
            'reason': reason,
            'next_invest_date': self._get_next_invest_date()
        }
    
    def _valuation_based_suggestion(
        self,
        base_amount: float,
        percentile: float
    ) -> Dict:
        """基于估值的定投建议"""
        # 估值分位数越低，定投倍数越高
        if percentile < 20:
            multiplier = 2.0  # 低估，加倍投
        elif percentile < 40:
            multiplier = 1.5
        elif percentile < 60:
            multiplier = 1.0  # 正常估值
        elif percentile < 80:
            multiplier = 0.5  # 高估，减半
        else:
            multiplier = 0.0  # 严重高估，暂停
        
        return {
            'amount': round(base_amount * multiplier, 2),
            'multiplier': multiplier
        }
    
    async def backtest_strategy(
        self,
        fund_code: str,
        base_amount: float,
        months: int = 12
    ) -> List[Dict]:
        """回测定投策略"""
        
        strategies = ['fixed', 'valuation', 'smart_add']
        results = []
        
        for strategy in strategies:
            # 模拟历史定投
            total_invest = 0
            total_shares = 0
            
            history = await self._get_history_for_backtest(fund_code, months)
            
            for month_data in history:
                nav = month_data['nav']
                
                # 根据策略确定当月金额
                if strategy == 'fixed':
                    amount = base_amount
                elif strategy == 'valuation':
                    percentile = month_data['percentile']
                    amount = base_amount * self._get_valuation_multiplier(percentile)
                else:  # smart_add
                    drop_pct = month_data.get('drop_from_last', 0)
                    amount = base_amount * (1 + max(0, drop_pct / 5))
                
                shares = amount / nav
                total_invest += amount
                total_shares += shares
            
            # 计算最终收益
            final_value = total_shares * history[-1]['nav']
            profit = final_value - total_invest
            profit_pct = (profit / total_invest) * 100
            
            results.append({
                'strategy': strategy,
                'strategy_name': self._get_strategy_name(strategy),
                'total_invest': round(total_invest, 2),
                'final_value': round(final_value, 2),
                'profit': round(profit, 2),
                'profit_pct': round(profit_pct, 2)
            })
        
        return sorted(results, key=lambda x: x['profit_pct'], reverse=True)
    
    async def _calculate_valuation_percentile(self, fund_code: str) -> float:
        """计算当前估值分位数"""
        # 获取近1年历史净值
        history = await history_service.get_history(fund_code, days=365)
        
        if not history:
            return 50.0
        
        navs = [h['nav'] for h in history]
        current_nav = navs[-1]
        
        # 计算分位数
        below_count = sum(1 for nav in navs if nav < current_nav)
        percentile = (below_count / len(navs)) * 100
        
        return round(percentile, 1)
```

---

## 4. 投资组合风险分析

### 4.1 功能概述

全面分析投资组合的风险指标，包括波动率、最大回撤、夏普比率等。

### 4.2 风险指标说明

| 指标 | 说明 | 参考值 |
|------|------|--------|
| 波动率 | 收益率的标准差 | <15% 低, 15-25% 中, >25% 高 |
| 最大回撤 | 从高点到低点的最大跌幅 | <10% 优秀, 10-20% 良好 |
| 夏普比率 | 风险调整后收益 | >1.0 良好, >2.0 优秀 |
| Beta | 相对市场波动 | =1 市场平均, <1 防御型 |
| VaR | 风险价值 | 95%置信度下的最大损失 |

### 4.3 后端设计

```python
# services/risk_analysis.py

import numpy as np
import pandas as pd
from typing import Dict, List
from scipy import stats

class RiskAnalysisService:
    """风险分析服务"""
    
    async def analyze_portfolio_risk(
        self,
        portfolio_items: List[Dict]
    ) -> Dict:
        """分析组合风险"""
        
        # 1. 获取组合历史收益
        portfolio_returns = await self._get_portfolio_returns(portfolio_items)
        
        if not portfolio_returns:
            return {'error': '无法获取历史数据'}
        
        returns_series = pd.Series(portfolio_returns)
        
        # 2. 计算各项指标
        risk_metrics = {
            'volatility': self._calculate_volatility(returns_series),
            'max_drawdown': self._calculate_max_drawdown(returns_series),
            'sharpe_ratio': self._calculate_sharpe_ratio(returns_series),
            'var_95': self._calculate_var(returns_series, 0.95),
            'beta': await self._calculate_beta(portfolio_items),
            'alpha': await self._calculate_alpha(portfolio_items)
        }
        
        # 3. 风险评级
        risk_level = self._assess_risk_level(risk_metrics)
        
        # 4. 行业分布
        sector_distribution = await self._analyze_sector_distribution(portfolio_items)
        
        return {
            'metrics': risk_metrics,
            'risk_level': risk_level,
            'sector_distribution': sector_distribution,
            'suggestions': self._generate_risk_suggestions(risk_metrics)
        }
    
    def _calculate_volatility(self, returns: pd.Series) -> Dict:
        """计算波动率"""
        # 年化波动率
        daily_vol = returns.std()
        annual_vol = daily_vol * np.sqrt(252)  # 252个交易日
        
        return {
            'daily': round(daily_vol * 100, 2),
            'annual': round(annual_vol * 100, 2),
            'level': self._get_volatility_level(annual_vol)
        }
    
    def _calculate_max_drawdown(self, returns: pd.Series) -> Dict:
        """计算最大回撤"""
        # 计算累计收益
        cumulative = (1 + returns).cumprod()
        
        # 计算回撤
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        
        max_dd = drawdown.min()
        
        # 找到回撤期间
        max_dd_end = drawdown.idxmin()
        max_dd_start = cumulative.loc[:max_dd_end].idxmax()
        
        return {
            'max_drawdown': round(abs(max_dd) * 100, 2),
            'start_date': max_dd_start,
            'end_date': max_dd_end,
            'recovery_days': self._estimate_recovery_days(returns, max_dd)
        }
    
    def _calculate_sharpe_ratio(self, returns: pd.Series, risk_free_rate: float = 0.03) -> Dict:
        """计算夏普比率"""
        excess_returns = returns.mean() * 252 - risk_free_rate
        volatility = returns.std() * np.sqrt(252)
        
        if volatility == 0:
            sharpe = 0
        else:
            sharpe = excess_returns / volatility
        
        return {
            'value': round(sharpe, 2),
            'level': self._get_sharpe_level(sharpe)
        }
    
    def _calculate_var(self, returns: pd.Series, confidence: float = 0.95) -> Dict:
        """计算风险价值 (VaR)"""
        var = np.percentile(returns, (1 - confidence) * 100)
        
        return {
            'var_95': round(abs(var) * 100, 2),
            'var_99': round(abs(np.percentile(returns, 1)) * 100, 2),
            'interpretation': f'单日损失超过{abs(var)*100:.2f}%的概率为{(1-confidence)*100:.0f}%'
        }
    
    def _assess_risk_level(self, metrics: Dict) -> str:
        """评估风险等级"""
        score = 0
        
        # 波动率评分
        vol = metrics['volatility']['annual']
        if vol < 15:
            score += 1
        elif vol > 25:
            score += 3
        else:
            score += 2
        
        # 最大回撤评分
        mdd = metrics['max_drawdown']['max_drawdown']
        if mdd < 10:
            score += 1
        elif mdd > 20:
            score += 3
        else:
            score += 2
        
        # 夏普比率评分
        sharpe = metrics['sharpe_ratio']['value']
        if sharpe > 1.5:
            score -= 1
        elif sharpe < 0.5:
            score += 1
        
        if score <= 3:
            return '低风险'
        elif score <= 5:
            return '中等风险'
        else:
            return '高风险'
```

---

## 5. 市场情绪指数

### 5.1 功能概述

基于全市场基金数据计算情绪指数，反映市场整体恐慌/贪婪程度。

### 5.2 指数计算

```python
# services/market_sentiment.py

from typing import Dict
import statistics

class MarketSentimentService:
    """市场情绪服务"""
    
    async def calculate_sentiment_index(self) -> Dict:
        """计算市场情绪指数"""
        
        # 1. 获取全市场基金数据
        all_funds = await self._get_all_fund_realtime_data()
        
        if not all_funds:
            return {'error': '无法获取市场数据'}
        
        # 2. 计算各项指标
        indicators = {
            'up_down_ratio': self._calc_up_down_ratio(all_funds),
            'avg_change': self._calc_average_change(all_funds),
            'extreme_ratio': self._calc_extreme_ratio(all_funds),
            'volume_trend': await self._calc_volume_trend(),
            'breadth': self._calc_market_breadth(all_funds)
        }
        
        # 3. 计算综合情绪指数 (0-100)
        # 50为中性，<50恐慌，>50贪婪
        sentiment_score = self._calc_sentiment_score(indicators)
        
        # 4. 确定情绪等级
        sentiment_level = self._get_sentiment_level(sentiment_score)
        
        return {
            'index': round(sentiment_score, 1),
            'level': sentiment_level,
            'indicators': indicators,
            'interpretation': self._get_interpretation(sentiment_score),
            'suggestion': self._get_suggestion(sentiment_score)
        }
    
    def _calc_up_down_ratio(self, funds: List[Dict]) -> Dict:
        """计算涨跌比"""
        up_count = sum(1 for f in funds if (f.get('estimate_change') or 0) > 0)
        down_count = sum(1 for f in funds if (f.get('estimate_change') or 0) < 0)
        flat_count = len(funds) - up_count - down_count
        
        total = up_count + down_count
        ratio = up_count / total if total > 0 else 1.0
        
        return {
            'up': up_count,
            'down': down_count,
            'flat': flat_count,
            'ratio': round(ratio, 2),
            'score': ratio * 100  # 0-100分
        }
    
    def _calc_average_change(self, funds: List[Dict]) -> Dict:
        """计算平均涨跌幅"""
        changes = [f.get('estimate_change', 0) for f in funds if f.get('estimate_change')]
        
        if not changes:
            return {'avg': 0, 'median': 0, 'score': 50}
        
        avg_change = statistics.mean(changes)
        median_change = statistics.median(changes)
        
        # 转换为0-100分
        # 假设正常范围 -3% 到 +3%
        score = min(100, max(0, (avg_change + 3) / 6 * 100))
        
        return {
            'avg': round(avg_change, 2),
            'median': round(median_change, 2),
            'score': round(score, 1)
        }
    
    def _calc_sentiment_score(self, indicators: Dict) -> float:
        """计算综合情绪指数"""
        weights = {
            'up_down_ratio': 0.30,
            'avg_change': 0.30,
            'extreme_ratio': 0.15,
            'volume_trend': 0.15,
            'breadth': 0.10
        }
        
        score = 0
        for key, weight in weights.items():
            if key in indicators and 'score' in indicators[key]:
                score += indicators[key]['score'] * weight
        
        return score
    
    def _get_sentiment_level(self, score: float) -> str:
        """获取情绪等级"""
        if score >= 80:
            return '极度贪婪'
        elif score >= 60:
            return '贪婪'
        elif score >= 40:
            return '中性'
        elif score >= 20:
            return '恐慌'
        else:
            return '极度恐慌'
    
    def _get_suggestion(self, score: float) -> str:
        """获取投资建议"""
        if score >= 75:
            return '市场情绪过热，建议适当减仓，保持谨慎'
        elif score >= 60:
            return '市场情绪偏乐观，可考虑分批减仓'
        elif score >= 40:
            return '市场情绪中性，维持现有配置'
        elif score >= 25:
            return '市场情绪偏悲观，可考虑逢低布局'
        else:
            return '市场恐慌情绪浓厚，可能是较好的买入时机'
```

---

## 6. 投资组合收益归因分析

### 6.1 功能概述

分析投资组合收益的来源，包括资产配置、行业选择、个股选择等因素的贡献。

### 6.2 归因模型

```python
# services/return_attribution.py

from typing import Dict, List
import pandas as pd

class ReturnAttributionService:
    """收益归因服务"""
    
    async def analyze_return_attribution(
        self,
        portfolio_items: List[Dict],
        start_date: str,
        end_date: str
    ) -> Dict:
        """分析收益归因"""
        
        # 1. 获取组合实际收益
        actual_return = await self._calculate_portfolio_return(
            portfolio_items, start_date, end_date
        )
        
        # 2. 资产配置归因
        allocation_attribution = await self._analyze_allocation_effect(
            portfolio_items, start_date, end_date
        )
        
        # 3. 行业选择归因
        sector_attribution = await self._analyze_sector_selection(
            portfolio_items, start_date, end_date
        )
        
        # 4. 个股选择归因
        stock_attribution = await self._analyze_stock_selection(
            portfolio_items, start_date, end_date
        )
        
        # 5. 交互效应
        interaction = actual_return - (
            allocation_attribution['contribution'] +
            sector_attribution['contribution'] +
            stock_attribution['contribution']
        )
        
        return {
            'period': {'start': start_date, 'end': end_date},
            'actual_return': round(actual_return * 100, 2),
            'attribution': {
                'allocation': allocation_attribution,
                'sector_selection': sector_attribution,
                'stock_selection': stock_attribution,
                'interaction': {
                    'contribution': round(interaction * 100, 2),
                    'percentage': round(interaction / actual_return * 100, 1) if actual_return != 0 else 0
                }
            },
            'summary': self._generate_attribution_summary(
                allocation_attribution,
                sector_attribution,
                stock_attribution
            )
        }
    
    async def _analyze_allocation_effect(
        self,
        portfolio_items: List[Dict],
        start_date: str,
        end_date: str
    ) -> Dict:
        """分析资产配置效应"""
        
        # 假设有基准配置（如股债50/50）
        benchmark_weights = {'equity': 0.5, 'bond': 0.3, 'cash': 0.2}
        
        # 实际配置
        actual_weights = self._calculate_actual_weights(portfolio_items)
        
        # 各类资产收益
        asset_returns = await self._get_asset_class_returns(start_date, end_date)
        
        # 计算配置效应
        allocation_contrib = 0
        for asset_class, weight in actual_weights.items():
            benchmark_weight = benchmark_weights.get(asset_class, 0)
            asset_return = asset_returns.get(asset_class, 0)
            allocation_contrib += (weight - benchmark_weight) * asset_return
        
        return {
            'contribution': round(allocation_contrib * 100, 2),
            'percentage': round(allocation_contrib / sum(asset_returns.values()) * 100, 1),
            'actual_weights': actual_weights,
            'benchmark_weights': benchmark_weights,
            'description': '由于超配/低配某些资产类别带来的收益差异'
        }
    
    async def _analyze_sector_selection(
        self,
        portfolio_items: List[Dict],
        start_date: str,
        end_date: str
    ) -> Dict:
        """分析行业选择效应"""
        
        # 获取各行业收益
        sector_returns = await self._get_sector_returns(start_date, end_date)
        
        # 组合行业权重
        portfolio_sector_weights = self._calculate_sector_weights(portfolio_items)
        
        # 基准行业权重（如沪深300行业分布）
        benchmark_sector_weights = await self._get_benchmark_sector_weights()
        
        # 计算行业选择效应
        sector_contrib = 0
        for sector, weight in portfolio_sector_weights.items():
            benchmark_weight = benchmark_sector_weights.get(sector, 0)
            sector_return = sector_returns.get(sector, 0)
            sector_contrib += (weight - benchmark_weight) * sector_return
        
        # 找出贡献最大的行业
        top_sectors = sorted(
            [(s, portfolio_sector_weights.get(s, 0) * sector_returns.get(s, 0)) 
             for s in set(portfolio_sector_weights.keys()) | set(benchmark_sector_weights.keys())],
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        return {
            'contribution': round(sector_contrib * 100, 2),
            'percentage': round(sector_contrib / sum(sector_returns.values()) * 100, 1) if sum(sector_returns.values()) != 0 else 0,
            'top_contributing_sectors': [
                {'sector': s, 'contribution': round(c * 100, 2)} 
                for s, c in top_sectors
            ],
            'description': '由于超配表现好的行业带来的收益'
        }
    
    def _generate_attribution_summary(
        self,
        allocation: Dict,
        sector: Dict,
        stock: Dict
    ) -> str:
        """生成归因总结"""
        
        parts = []
        
        # 资产配置贡献
        alloc_contrib = allocation['contribution']
        if alloc_contrib > 0.5:
            parts.append(f"资产配置带来{alloc_contrib}%的正贡献")
        elif alloc_contrib < -0.5:
            parts.append(f"资产配置造成{abs(alloc_contrib)}%的负贡献")
        
        # 行业选择贡献
        sector_contrib = sector['contribution']
        if sector_contrib > 0.5:
            parts.append(f"行业选择带来{sector_contrib}%的正贡献")
        elif sector_contrib < -0.5:
            parts.append(f"行业选择造成{abs(sector_contrib)}%的负贡献")
        
        # 个股选择贡献
        stock_contrib = stock['contribution']
        if stock_contrib > 0.5:
            parts.append(f"个股选择带来{stock_contrib}%的正贡献")
        elif stock_contrib < -0.5:
            parts.append(f"个股选择造成{abs(stock_contrib)}%的负贡献")
        
        if not parts:
            return "各因素贡献相对均衡"
        
        return "；".join(parts)
```

---

## 附录

### A. 数据表设计

```sql
-- 相关性分析记录
CREATE TABLE fund_correlations (
    id INTEGER PRIMARY KEY,
    fund_code_1 VARCHAR(10),
    fund_code_2 VARCHAR(10),
    correlation FLOAT,
    period_days INTEGER,
    calculation_date DATE,
    updated_at TIMESTAMP
);

-- 估值历史记录
CREATE TABLE estimate_history (
    id INTEGER PRIMARY KEY,
    fund_code VARCHAR(10),
    estimate_date DATE,
    estimate_nav FLOAT,
    actual_nav FLOAT,
    data_source VARCHAR(50),
    created_at TIMESTAMP
);

-- 市场情绪指数
CREATE TABLE market_sentiment (
    id INTEGER PRIMARY KEY,
    sentiment_date DATE,
    sentiment_index FLOAT,
    level VARCHAR(20),
    indicators JSON,
    created_at TIMESTAMP
);

-- 定投计划
CREATE TABLE invest_plans (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    fund_code VARCHAR(10),
    strategy VARCHAR(20),
    base_amount FLOAT,
    current_amount FLOAT,
    next_invest_date DATE,
    is_active BOOLEAN,
    created_at TIMESTAMP
);
```

### B. API汇总

| 接口 | 方法 | 描述 |
|------|------|------|
| /api/v1/analysis/correlation | POST | 计算相关性矩阵 |
| /api/v1/analysis/backtest | POST | 估值回溯分析 |
| /api/v1/analysis/smart-invest | POST | 智能定投建议 |
| /api/v1/analysis/risk | POST | 风险分析 |
| /api/v1/analysis/sentiment | GET | 市场情绪指数 |
| /api/v1/analysis/attribution | POST | 收益归因分析 |

---

*本文档详细描述了投资分析类功能的设计，供开发参考。*
