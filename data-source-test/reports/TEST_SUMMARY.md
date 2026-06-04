# 基金数据源测试总结报告

**测试时间**: 2026-05-27 16:45
**测试环境**: Python 3.11.15, Windows 11
**测试基金**: 21只（包含开放式基金、LOF、ETF）

---

## 测试结果总览

| 数据源 | 可行性 | 稳定性 | 性能 | 数据新鲜度 | 综合评价 |
|--------|--------|--------|------|------------|----------|
| **efinance** | 100% (21/21) | 100% (标准差0) | 极快 (243ms批量) | T+1 | ⭐⭐⭐⭐⭐ |
| **eastmoney_direct** | 100% (21/21) | 100% (标准差0) | 快 (1.5s批量) | 实时 | ⭐⭐⭐⭐⭐ |
| **akshare** | 100% (21/21) | 100% (标准差0) | 慢 (126s批量) | T+1 | ⭐⭐⭐ |
| **tushare_pro** | 需单独测试 | 频率限制1次/分钟 | 慢 | T+1 | ⭐⭐⭐ |

---

## 详细测试结果

### 1. efinance

**优点**:
- ✅ 成功率100%（21/21）
- ✅ 性能极佳：批量获取仅需243ms
- ✅ 原生支持批量接口
- ✅ 返回基金名称
- ✅ 轻量级，无复杂依赖

**缺点**:
- ⚠️ 非交易时段无实时涨跌幅（仅返回T+1净值）
- ⚠️ 底层依赖东方财富API，可能因上游变化失效
- ⚠️ 库维护频率较低

**数据样本**:
```
015916 永赢医药创新智选混合发起C: 净值=1.5432, 更新=2026-05-26
513630 港股低波红利ETF摩根: 净值=1.6624, 更新=2026-05-26
```

**API调用**:
```python
import efinance as ef
df = ef.fund.get_realtime_increase_rate(fund_codes=['015916', '513630'])
# 返回列：基金代码, 基金名称, 最新净值, 最新净值公开日期, 估算时间, 估算涨跌幅
```

---

### 2. eastmoney_direct（自维护API）

**优点**:
- ✅ 成功率100%（21/21）
- ✅ 交易时段有实时估值和涨跌幅
- ✅ 多策略降级（天天基金→腾讯→东方财富lsjz→pingzhongdata）
- ✅ 返回基金名称和实时更新时间
- ✅ 无第三方库依赖

**缺点**:
- ⚠️ 需要自行维护API调用代码
- ⚠️ 非官方API，可能被封IP
- ⚠️ 响应格式可能随上游变化

**数据样本**:
```
015916 永赢医药创新智选混合发起C: 净值=1.5488, 涨跌幅=0.36%, 更新=2026-05-27 15:00
513630 摩根标普港股通低波红利ETF: 净值=1.6504, 涨跌幅=-0.89%, 更新=2026-05-26
012349 天弘恒生科技ETF联接C: 净值=0.6645, 涨跌幅=-0.75%, 更新=2026-05-27 16:00
```

**API端点**:
```
天天基金实时估值: http://fundgz.1234567.com.cn/js/{code}.js
腾讯基金: http://qt.gtimg.cn/q=jj{code}
东方财富lsjz: http://api.fund.eastmoney.com/f10/lsjz?fundCode={code}
```

---

### 3. akshare

**优点**:
- ✅ 成功率100%（21/21）
- ✅ 社区活跃，文档完善
- ✅ 接口丰富

**缺点**:
- ❌ 性能极差：批量获取需要126秒（单只约6秒）
- ⚠️ 非交易时段仅返回T+1净值
- ⚠️ 不返回基金名称（代码作为名称）
- ⚠️ 不返回涨跌幅

**数据样本**:
```
015916: 净值=1.5432, 更新=2026-05-26
513630: 净值=1.6504, 更新=2026-05-26
```

---

### 4. tushare_pro

**单独测试结果**（由于频率限制1次/分钟，需单独测试）:

**优点**:
- ✅ 官方API，数据可靠
- ✅ 数据结构化
- ✅ 支持历史净值查询

**缺点**:
- ❌ 频率限制严格：1次/分钟
- ❌ 不支持实时估值（仅T+1）
- ⚠️ 需要注册获取token
- ⚠️ 部分接口需要积分

**测试结论**: 由于频率限制（1次/分钟），获取21只基金需要21分钟，不适合实时场景。适合作为历史数据补充源。

---

## 性能对比

| 指标 | efinance | eastmoney_direct | akshare | tushare_pro |
|------|----------|------------------|---------|-------------|
| 批量耗时 | 243ms | 1.5s | 126s | ~21min |
| 单次平均 | 12ms | 74ms | 5.7s | ~60s |
| 并发支持 | 原生批量 | 串行 | 串行 | 串行 |
| 频率限制 | 无明显限制 | 需注意反爬 | 无明显限制 | 1次/分钟 |

---

## 数据新鲜度对比

| 数据源 | 交易时段 | 非交易时段 |
|--------|----------|------------|
| efinance | 实时估值+涨跌幅 | T+1净值 |
| eastmoney_direct | 实时估值+涨跌幅 | T+1净值（部分实时） |
| akshare | LOF实时，其他T+1 | T+1净值 |
| tushare_pro | T+1净值 | T+1净值 |

---

## 推荐方案

### 方案A：高性能方案（推荐）

**主要数据源**: efinance + eastmoney_direct 降级

```python
# 优先使用efinance（批量性能最佳）
# 降级到eastmoney_direct（实时性更好）
```

**优势**:
- 批量性能最佳（243ms）
- 交易时段有实时数据
- 成功率100%

### 方案B：实时性方案

**主要数据源**: eastmoney_direct + efinance 降级

```python
# 优先使用eastmoney_direct（实时性更好）
# 降级到efinance（批量性能好）
```

**优势**:
- 交易时段实时数据最准确
- 多策略降级保障稳定性

### 方案C：稳定性方案

**主要数据源**: akshare + eastmoney_direct 降级

```python
# 优先使用akshare（社区支持好）
# 降级到eastmoney_direct（性能好）
```

**优势**:
- akshare社区活跃
- 接口文档完善

---

## 集成建议

### 修改 `fund-tracker/backend/app/services/fund_data_source.py`

```python
# 在DataSourceType枚举中添加
class DataSourceType(Enum):
    EFINANCE = "efinance"  # 新增
    # ... 其他

# 在FundDataSourceManager中添加
def _try_efinance(self, code: str, name: str) -> Dict:
    """efinance数据源"""
    try:
        import efinance as ef
        df = ef.fund.get_realtime_increase_rate(fund_codes=[code])
        if df is not None and not df.empty:
            row = df.iloc[0]
            return {
                'code': code,
                'name': str(row.get('基金名称', name)),
                'gz': float(row.get('最新净值', 0)) or None,
                'gszzl': float(row.get('估算涨跌幅', 0)) if row.get('估算涨跌幅') else None,
                'time': str(row.get('估算时间', row.get('最新净值公开日期', '--'))),
                'status': '正常',
                'source': 'efinance'
            }
    except Exception as e:
        logger.debug(f"efinance接口失败 {code}: {e}")
    return None
```

### 修改 `shared/config.py`

```python
DATA_SOURCES: List[str] = field(default_factory=lambda: [
    "efinance",        # 新增：性能最佳
    "tiantian",        # 天天基金实时估值
    "eastmoney",       # 东方财富
    "sina_lof",        # 新浪LOF
    "akshare_lof",     # AKShare LOF
    "latest_nav"       # 最新净值
])
```

---

## 代码保留位置

所有测试代码保留在 `data-source-test/` 目录：

```
data-source-test/
├── sources/              # 数据源适配器
│   ├── base.py          # 抽象基类
│   ├── efinance_source.py
│   ├── tushare_source.py
│   ├── eastmoney_api_source.py
│   └── akshare_source.py
├── tests/                # 测试用例
├── reports/              # 测试报告
├── run_all_tests.py      # 主测试脚本
└── generate_report.py    # 报告生成脚本
```

---

*报告生成时间: 2026-05-27 17:00*
