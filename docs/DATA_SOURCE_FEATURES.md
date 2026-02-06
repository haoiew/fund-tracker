# 数据源功能详细设计文档

> 基于多数据源架构的高级功能设计
> 版本: v1.0.0
> 更新时间: 2026-02-06

---

## 目录

1. [数据源健康度监控面板](#1-数据源健康度监控面板)
2. [多数据源对比视图](#2-多数据源对比视图)
3. [基金数据质量评分](#3-基金数据质量评分)
4. [智能数据补全](#4-智能数据补全)
5. [数据源自定义配置](#5-数据源自定义配置)

---

## 1. 数据源健康度监控面板

### 1.1 功能概述

实时监控各数据源的可用性、响应时间、成功率等关键指标，帮助用户了解当前数据质量，增强系统可信度。

### 1.2 用户界面设计

#### 监控仪表盘布局

```
┌─────────────────────────────────────────────────────────────┐
│                    数据源健康度监控                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │  天天基金    │ │   腾讯基金   │ │   新浪LOF   │           │
│  │   🟢 正常   │ │   🟢 正常   │ │   🟡 延迟   │           │
│  │  响应: 120ms│ │  响应: 80ms │ │  响应: 2.5s │           │
│  │  成功率:98% │ │  成功率:95% │ │  成功率:85% │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
├─────────────────────────────────────────────────────────────┤
│                    实时响应时间趋势                          │
│  [折线图: 各数据源最近1小时响应时间]                         │
├─────────────────────────────────────────────────────────────┤
│                    数据源可用性统计                          │
│  [饼图: 各数据源请求占比]                                    │
├─────────────────────────────────────────────────────────────┤
│  最近异常记录                                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 时间        │ 数据源   │ 异常类型     │ 状态      │   │
│  │ 15:23:45   │ 新浪LOF │ 请求超时     │ 已恢复    │   │
│  │ 14:56:12   │ 腾讯基金│ 返回空数据   │ 已恢复    │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 后端设计

#### 数据模型

```python
# models/datasource.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from app.db.base import Base

class DataSourceMetric(Base):
    """数据源指标记录"""
    __tablename__ = "data_source_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(String(50), index=True)  # tiantian, tencent, sina_lof等
    metric_timestamp = Column(DateTime, default=datetime.utcnow)
    
    # 请求统计
    total_requests = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)
    
    # 响应时间（毫秒）
    avg_response_time = Column(Float, default=0.0)
    min_response_time = Column(Float, default=0.0)
    max_response_time = Column(Float, default=0.0)
    
    # 状态
    is_available = Column(Boolean, default=True)
    last_success_time = Column(DateTime)
    last_fail_time = Column(DateTime)
    error_message = Column(String(500))


class DataSourceHealth(Base):
    """数据源健康状态（实时）"""
    __tablename__ = "data_source_health"
    
    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(String(50), unique=True, index=True)
    
    # 健康度评分 (0-100)
    health_score = Column(Integer, default=100)
    
    # 状态: healthy, degraded, down
    status = Column(String(20), default="healthy")
    
    # 统计周期（最近5分钟）
    requests_5m = Column(Integer, default=0)
    success_rate_5m = Column(Float, default=100.0)
    avg_response_time_5m = Column(Float, default=0.0)
    
    updated_at = Column(DateTime, default=datetime.utcnow)
```

#### 服务实现

```python
# services/datasource_monitor.py
import time
from datetime import datetime, timedelta
from typing import Dict, List
from collections import defaultdict
import asyncio

class DataSourceMonitor:
    """数据源监控服务"""
    
    def __init__(self):
        self.metrics_buffer = defaultdict(list)  # 内存缓冲区
        self.health_status = {}
        
    async def record_request(
        self,
        source_type: str,
        success: bool,
        response_time: float,
        error_msg: str = None
    ):
        """记录一次请求指标"""
        metric = {
            'timestamp': datetime.utcnow(),
            'success': success,
            'response_time': response_time,
            'error_msg': error_msg
        }
        self.metrics_buffer[source_type].append(metric)
        
        # 更新实时健康状态
        await self._update_health_status(source_type)
        
    async def _update_health_status(self, source_type: str):
        """更新数据源健康状态"""
        metrics = self.metrics_buffer[source_type]
        
        # 只保留最近5分钟的数据
        cutoff = datetime.utcnow() - timedelta(minutes=5)
        recent_metrics = [m for m in metrics if m['timestamp'] > cutoff]
        self.metrics_buffer[source_type] = recent_metrics
        
        if not recent_metrics:
            return
            
        # 计算指标
        total = len(recent_metrics)
        success_count = sum(1 for m in recent_metrics if m['success'])
        success_rate = (success_count / total) * 100 if total > 0 else 0
        avg_time = sum(m['response_time'] for m in recent_metrics) / total
        
        # 计算健康度评分
        health_score = self._calculate_health_score(success_rate, avg_time)
        
        # 确定状态
        if success_rate >= 95 and avg_time < 1000:
            status = "healthy"
        elif success_rate >= 80 and avg_time < 3000:
            status = "degraded"
        else:
            status = "down"
            
        self.health_status[source_type] = {
            'health_score': health_score,
            'status': status,
            'requests_5m': total,
            'success_rate_5m': success_rate,
            'avg_response_time_5m': avg_time,
            'updated_at': datetime.utcnow()
        }
        
    def _calculate_health_score(self, success_rate: float, avg_time: float) -> int:
        """计算健康度评分"""
        # 成功率权重 70%
        success_score = success_rate * 0.7
        
        # 响应时间权重 30%
        if avg_time < 200:
            time_score = 30
        elif avg_time < 500:
            time_score = 25
        elif avg_time < 1000:
            time_score = 20
        elif avg_time < 2000:
            time_score = 15
        else:
            time_score = 10
            
        return int(success_score + time_score)
        
    async def get_health_summary(self) -> Dict:
        """获取所有数据源健康摘要"""
        return self.health_status
        
    async def get_metrics_history(
        self,
        source_type: str,
        hours: int = 24
    ) -> List[Dict]:
        """获取历史指标"""
        # 从数据库查询历史数据
        pass
```

#### API端点

```python
# api/v1/datasource.py
from fastapi import APIRouter, Depends
from typing import List, Dict

router = APIRouter()

@router.get("/metrics", response_model=Dict)
async def get_datasource_metrics():
    """获取所有数据源当前指标"""
    monitor = get_datasource_monitor()
    return await monitor.get_health_summary()

@router.get("/metrics/{source_type}/history")
async def get_source_metrics_history(
    source_type: str,
    hours: int = 24
):
    """获取指定数据源历史指标"""
    monitor = get_datasource_monitor()
    return await monitor.get_metrics_history(source_type, hours)

@router.get("/health", response_model=Dict)
async def get_datasource_health():
    """获取数据源健康状态摘要"""
    pass
```

### 1.4 前端实现

```typescript
// views/DataSource/DataSourceMonitorView.vue
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'

const healthData = ref({})
const metricsHistory = ref([])
let refreshTimer: number

// 获取健康数据
const fetchHealthData = async () => {
  const res = await fetch('/api/v1/datasource/metrics')
  healthData.value = await res.json()
}

// 初始化图表
const initCharts = () => {
  // 响应时间趋势图
  const timeChart = echarts.init(document.getElementById('response-time-chart'))
  // 可用性饼图
  const pieChart = echarts.init(document.getElementById('availability-pie'))
}

// 自动刷新
onMounted(() => {
  fetchHealthData()
  refreshTimer = window.setInterval(fetchHealthData, 30000) // 30秒刷新
  initCharts()
})

onUnmounted(() => {
  clearInterval(refreshTimer)
})
```

---

## 2. 多数据源对比视图

### 2.1 功能概述

同时展示多个数据源的估值数据，帮助用户了解数据差异，选择最可信的数据源。

### 2.2 用户界面设计

```
┌─────────────────────────────────────────────────────────────┐
│                    多数据源对比                              │
├─────────────────────────────────────────────────────────────┤
│  基金: [016531 鹏华碳中和主题混合C ▼]  [刷新]               │
├─────────────────────────────────────────────────────────────┤
│  数据源对比                                                  │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐  │
│  │ 数据源   │ 估算净值 │ 涨跌幅   │ 更新时间 │ 状态    │  │
│  ├──────────┼──────────┼──────────┼──────────┼──────────┤  │
│  │ 天天基金 │ 1.2345   │ +2.34%   │ 15:23:45 │ ✅ 正常 │  │
│  │ 腾讯基金 │ 1.2340   │ +2.30%   │ 15:23:40 │ ✅ 正常 │  │
│  │ 新浪LOF  │ 1.2350   │ +2.38%   │ 15:23:30 │ ⚠️ 延迟│  │
│  │ 最新净值 │ 1.2300   │ --       │ 昨日     │ 📊 备份│  │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘  │
├─────────────────────────────────────────────────────────────┤
│  差异分析                                                    │
│  最大差异: 0.41% (新浪LOF vs 最新净值)                       │
│  平均差异: 0.15%                                            │
│  数据一致性: ⭐⭐⭐⭐☆ (良好)                                 │
├─────────────────────────────────────────────────────────────┤
│  历史对比趋势                                                │
│  [折线图: 各数据源净值历史对比]                              │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 后端设计

```python
# services/datasource_compare.py

class DataSourceCompareService:
    """数据源对比服务"""
    
    async def compare_fund_sources(self, code: str) -> Dict:
        """对比某只基金在所有数据源的数据"""
        from app.services.fund_data_source import get_data_source_manager
        
        ds_manager = get_data_source_manager()
        name = self._get_fund_name(code)
        
        # 获取所有数据源数据
        results = await ds_manager.fetch_all_sources(code, name)
        
        # 构建对比数据
        comparison = []
        nav_values = []
        
        for result in results:
            if result.is_valid and result.data.get('gz'):
                comparison.append({
                    'source': result.source_type.value,
                    'nav': float(result.data['gz']),
                    'change': result.data.get('gszzl'),
                    'update_time': result.data.get('time'),
                    'status': result.data.get('status'),
                    'priority': result.priority.name
                })
                nav_values.append(float(result.data['gz']))
        
        # 计算差异
        analysis = self._analyze_differences(nav_values)
        
        return {
            'fund_code': code,
            'fund_name': name,
            'comparisons': comparison,
            'analysis': analysis
        }
    
    def _analyze_differences(self, values: List[float]) -> Dict:
        """分析数据差异"""
        if len(values) < 2:
            return {'consistency_score': 100}
            
        max_val = max(values)
        min_val = min(values)
        avg_val = sum(values) / len(values)
        
        max_diff_pct = ((max_val - min_val) / avg_val) * 100
        
        # 计算一致性评分
        if max_diff_pct < 0.1:
            score = 100
        elif max_diff_pct < 0.3:
            score = 90
        elif max_diff_pct < 0.5:
            score = 80
        elif max_diff_pct < 1.0:
            score = 70
        else:
            score = 60
            
        return {
            'max_difference': round(max_val - min_val, 4),
            'max_diff_percentage': round(max_diff_pct, 2),
            'average_nav': round(avg_val, 4),
            'consistency_score': score,
            'consistency_level': self._get_consistency_level(score)
        }
    
    def _get_consistency_level(self, score: int) -> str:
        if score >= 90:
            return "优秀"
        elif score >= 80:
            return "良好"
        elif score >= 70:
            return "一般"
        else:
            return "较差"
```

### 2.4 API端点

```python
@router.get("/compare/{code}")
async def compare_fund_data_sources(code: str):
    """对比某只基金的多数据源数据"""
    service = DataSourceCompareService()
    return await service.compare_fund_sources(code)
```

---

## 3. 基金数据质量评分

### 3.1 功能概述

基于多数据源对比、历史准确率等因素，给基金数据质量打分，帮助用户了解数据可信度。

### 3.2 评分算法

```python
# services/data_quality.py

class DataQualityScorer:
    """数据质量评分服务"""
    
    def calculate_quality_score(self, code: str) -> Dict:
        """计算基金数据质量评分"""
        
        # 1. 多源一致性评分 (40%)
        consistency_score = self._calc_consistency_score(code)
        
        # 2. 数据新鲜度评分 (30%)
        freshness_score = self._calc_freshness_score(code)
        
        # 3. 历史准确率评分 (30%)
        accuracy_score = self._calc_accuracy_score(code)
        
        # 加权总分
        total_score = (
            consistency_score * 0.4 +
            freshness_score * 0.3 +
            accuracy_score * 0.3
        )
        
        return {
            'fund_code': code,
            'total_score': round(total_score, 1),
            'grade': self._score_to_grade(total_score),
            'details': {
                'consistency': {
                    'score': round(consistency_score, 1),
                    'weight': 40,
                    'description': '多数据源一致性'
                },
                'freshness': {
                    'score': round(freshness_score, 1),
                    'weight': 30,
                    'description': '数据新鲜度'
                },
                'accuracy': {
                    'score': round(accuracy_score, 1),
                    'weight': 30,
                    'description': '历史准确率'
                }
            }
        }
    
    def _calc_consistency_score(self, code: str) -> float:
        """计算一致性评分"""
        # 获取多源对比结果
        comparison = self._get_source_comparison(code)
        return comparison.get('consistency_score', 50)
    
    def _calc_freshness_score(self, code: str) -> float:
        """计算新鲜度评分"""
        # 获取最新数据时间
        latest_data = self._get_latest_data(code)
        if not latest_data:
            return 0
            
        update_time = latest_data.get('update_time')
        if not update_time or update_time == '--':
            return 50
            
        try:
            # 解析时间
            from datetime import datetime
            data_time = datetime.strptime(update_time, '%H:%M:%S')
            now = datetime.now()
            
            # 计算分钟差
            diff_minutes = (now.hour - data_time.hour) * 60 + (now.minute - data_time.minute)
            
            if diff_minutes < 5:
                return 100
            elif diff_minutes < 15:
                return 90
            elif diff_minutes < 30:
                return 80
            elif diff_minutes < 60:
                return 70
            else:
                return 60
        except:
            return 50
    
    def _calc_accuracy_score(self, code: str) -> float:
        """计算历史准确率评分"""
        # 从历史记录中计算
        history = self._get_estimate_history(code, days=30)
        
        if not history or len(history) < 5:
            return 75  # 默认中等评分
            
        # 计算平均误差
        errors = []
        for record in history:
            if record.get('estimate_nav') and record.get('actual_nav'):
                error = abs(record['estimate_nav'] - record['actual_nav'])
                errors.append(error)
        
        if not errors:
            return 75
            
        avg_error = sum(errors) / len(errors)
        
        # 误差越小，分数越高
        if avg_error < 0.001:
            return 100
        elif avg_error < 0.003:
            return 90
        elif avg_error < 0.005:
            return 80
        elif avg_error < 0.01:
            return 70
        else:
            return 60
    
    def _score_to_grade(self, score: float) -> str:
        if score >= 90:
            return 'A'
        elif score >= 80:
            return 'B'
        elif score >= 70:
            return 'C'
        elif score >= 60:
            return 'D'
        else:
            return 'E'
```

---

## 4. 智能数据补全

### 4.1 功能概述

当主数据源缺失某些字段时，自动从其他数据源补全，提高数据完整性。

### 4.2 补全策略

```python
# services/data_completion.py

class DataCompletionService:
    """数据补全服务"""
    
    # 字段补全优先级
    FIELD_PRIORITY = {
        'estimate_nav': ['天天基金', '腾讯基金', '新浪LOF', 'AKShare LOF'],
        'estimate_change': ['天天基金', '腾讯基金', '新浪LOF'],
        'previous_nav': ['天天基金', '最新净值'],
        'update_time': ['天天基金', '腾讯基金', '新浪LOF'],
    }
    
    async def complete_fund_data(self, code: str, base_data: Dict) -> Dict:
        """补全基金数据"""
        completed_data = base_data.copy()
        completion_log = []
        
        # 检查缺失字段
        for field, priority_sources in self.FIELD_PRIORITY.items():
            if not completed_data.get(field) or completed_data[field] == '--':
                # 尝试从其他数据源获取
                for source_name in priority_sources:
                    value = await self._get_field_from_source(
                        code, field, source_name
                    )
                    if value:
                        completed_data[field] = value
                        completion_log.append({
                            'field': field,
                            'source': source_name,
                            'original_value': base_data.get(field),
                            'completed_value': value
                        })
                        break
        
        completed_data['_completion_log'] = completion_log
        completed_data['_completion_count'] = len(completion_log)
        
        return completed_data
    
    async def _get_field_from_source(
        self,
        code: str,
        field: str,
        source_name: str
    ) -> Any:
        """从指定数据源获取字段"""
        # 实现从特定数据源获取字段的逻辑
        pass
```

---

## 5. 数据源自定义配置

### 5.1 功能概述

允许用户自定义数据源的启用状态、优先级和超时设置。

### 5.2 配置项设计

```python
# schemas/datasource.py

from pydantic import BaseModel
from typing import List, Optional

class DataSourceConfig(BaseModel):
    """数据源配置"""
    source_type: str
    name: str
    is_enabled: bool = True
    priority: int = 1  # 1=高, 2=中, 3=低
    timeout: float = 5.0  # 秒
    max_retries: int = 2
    weight: float = 1.0  # 权重，用于加权平均

class DataSourceSettings(BaseModel):
    """数据源全局设置"""
    sources: List[DataSourceConfig]
    
    # 全局策略
    auto_fallback: bool = True  # 自动降级
    parallel_fetch: bool = True  # 并行获取
    max_parallel: int = 5  # 最大并行数
    
    # 数据选择策略
    selection_strategy: str = "priority"  # priority, weighted_avg, best_available
    freshness_threshold: int = 60  # 分钟，超过则视为不新鲜
```

### 5.3 前端界面

```
┌─────────────────────────────────────────────────────────────┐
│                    数据源配置                                │
├─────────────────────────────────────────────────────────────┤
│  拖动排序以调整优先级:                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ☰ 天天基金    [启用 ☑]  超时: 5000ms  [删除]       │   │
│  │ ☰ 腾讯基金    [启用 ☑]  超时: 3000ms  [删除]       │   │
│  │ ☰ 新浪LOF     [启用 ☐]  超时: 5000ms  [删除]       │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  全局设置                                                    │
│  [☑] 自动降级                                                │
│  [☑] 并行获取数据                                            │
│  最大并行数: [5]                                             │
│  数据新鲜度阈值: [60] 分钟                                   │
├─────────────────────────────────────────────────────────────┤
│  数据选择策略:                                               │
│  (•) 优先级优先                                              │
│  ( ) 加权平均                                                │
│  ( ) 最佳可用                                                │
├─────────────────────────────────────────────────────────────┤
│              [保存配置]  [重置默认]  [测试连接]             │
└─────────────────────────────────────────────────────────────┘
```

---

## 附录

### A. 数据库迁移脚本

```sql
-- 创建数据源相关表
CREATE TABLE IF NOT EXISTS data_source_configs (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    source_type VARCHAR(50),
    name VARCHAR(100),
    is_enabled BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 1,
    timeout FLOAT DEFAULT 5.0,
    max_retries INTEGER DEFAULT 2,
    weight FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dsc_user ON data_source_configs(user_id);
```

### B. 接口汇总

| 接口 | 方法 | 描述 |
|------|------|------|
| /api/v1/datasource/metrics | GET | 获取数据源指标 |
| /api/v1/datasource/health | GET | 获取健康状态 |
| /api/v1/datasource/compare/{code} | GET | 对比多数据源 |
| /api/v1/datasource/quality/{code} | GET | 获取数据质量评分 |
| /api/v1/datasource/config | GET/PUT | 获取/更新配置 |
| /api/v1/datasource/test | POST | 测试数据源连接 |

---

*本文档详细描述了基于多数据源架构的高级功能设计，供开发参考。*
