## 数据源分析总结

### 腾讯基金 (qt.gtimg.cn)
**返回格式**:
```python
['007722', '天弘标普500发起(QDII-FOF)C', '0.0000', '0.0000', '', '2.0299', '2.0299', '-1.0963', '2026-02-05', '']
# 索引: 0         1                         2         3         4   5         6         7          8            9
```
- 索引5: 净值 **2.0299** ✅
- 索引7: 涨跌幅 **-1.0963%** ✅
- **最佳数据源**

### 东方财富 (fund.eastmoney.com)
**返回格式**:
- `Data_netWorthTrend`: 净值历史数组
- 最新净值: **2.0299**
- 可计算日涨跌幅: **-1.10%**
- **可靠备用源**

### 新浪LOF
- 网络超时，当前不可用 ❌

## 修复方案

### 1. 修复腾讯基金接口
修改 `_try_tencent_fund` 方法，使用索引5作为净值来源：

```python
def _try_tencent_fund(self, code: str, name: str) -> Dict:
    # ...
    if len(parts) > 8:
        # QDII基金最新价(parts[2])为0，使用净值(parts[5])
        price_str = parts[2].strip()
        nav_str = parts[5].strip() if len(parts) > 5 else ''  # 净值字段
        change_str = parts[7].strip() if len(parts) > 7 else ''
        
        # 优先使用最新价，如果为0则使用净值
        if price_str and price_str not in ['0.00', '0.0000', '0', '']:
            item['gz'] = float(price_str)
        elif nav_str and nav_str not in ['0.00', '0.0000', '0', '']:
            item['gz'] = float(nav_str)
        
        # 涨跌幅
        if change_str and change_str not in ['0.00', '0.0000', '0', '']:
            item['gszzl'] = float(change_str)
        
        if item['gz'] or item['gszzl']:
            item['status'] = '正常'
            return item
```

### 2. 添加东方财富作为备用源
新增 `_try_eastmoney` 方法：

```python
def _try_eastmoney(self, code: str, name: str) -> Dict:
    """东方财富数据源 - 提供历史净值"""
    item = {
        'code': code, 'name': name, 'gz': None, 'gszzl': None,
        'time': '--', 'status': '获取中', 'source': '东方财富'
    }
    try:
        url = f"http://fund.eastmoney.com/pingzhongdata/{code}.js"
        resp = self.session.get(url, timeout=5)
        if resp.status_code == 200:
            # 解析净值历史数据
            import re, json
            match = re.search(r'var Data_netWorthTrend = (\[.*?\]);', resp.text, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                if len(data) >= 2:
                    latest = data[-1]
                    prev = data[-2]
                    item['gz'] = latest.get('y')
                    item['time'] = latest.get('x')
                    # 计算涨跌幅
                    if prev.get('y', 0) > 0:
                        item['gszzl'] = round((latest['y'] - prev['y']) / prev['y'] * 100, 2)
                    item['status'] = '正常'
                    return item
        item['status'] = '无数据'
    except Exception as e:
        item['status'] = f'错误: {str(e)[:20]}'
    return item
```

## 实施计划

1. 修复腾讯基金接口 (`fund_data_source.py`)
2. 添加东方财富数据源 (`fund_data_source.py`)
3. 更新数据源优先级配置
4. 测试验证

请确认后我将实施修复。