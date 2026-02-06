## 问题总结

### 1. **重复基金代码问题**
日志显示：
```
批量获取基金实时估值: ['012349', '012349', '012349', '012349', '012349', ...]
```
- 012349 重复 5 次
- 015916 重复 9 次
- 017436 重复 9 次
- 018125 重复 15 次

### 2. **chart_config 未定义错误**
```
NameError: name 'chart_config' is not defined
File ".../funds.py", line 200
```

## 修复计划

### 修复1：DataManager 添加去重逻辑
- 在 `loadRealtimeData` 方法中使用 `Set` 去重
- 确保请求 key 基于去重后的代码生成

### 修复2：后端API添加去重保护
- 在 `get_funds_realtime` 方法开头添加 `codes = list(set(codes))`
- 导入 `chart_config` 模块修复对比API

### 修复3：检查数据源
- 检查 `localStorage` 中的基金列表是否有重复
- 检查持仓数据与基金列表的合并逻辑