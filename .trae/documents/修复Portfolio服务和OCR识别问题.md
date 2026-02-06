## 问题分析

从截图和日志发现了两个问题：

### 问题1：Portfolio服务报错
```
AttributeError: 'dict' object has no attribute 'estimate_nav'
File: portfolio_service.py, line 175
```

`realtime` 是字典对象，但代码使用了点号访问属性。

### 问题2：OCR识别失败
截图显示"未识别到基金持仓信息"，说明OCR识别逻辑有问题。

## 修复方案

### 1. 修复Portfolio服务

修改 `app/services/portfolio_service.py` 第175行：
```python
# 错误
if realtime.estimate_nav and portfolio.hold_shares:

# 正确
if realtime.get('estimate_nav') and portfolio.hold_shares:
```

### 2. 增强OCR调试和修复

添加详细日志来诊断OCR识别失败的原因：
- 打印OCR识别到的原始文本
- 打印提取的基金名称
- 打印匹配结果

### 3. 修复OCR识别逻辑

可能需要调整：
- 基金名称识别规则
- 数值提取规则
- 匹配阈值

## 实施步骤

1. 修复Portfolio服务的字典访问问题
2. 添加OCR调试日志
3. 测试OCR识别
4. 根据测试结果调整识别逻辑

预计时间：1-2小时