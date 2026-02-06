## 计算结果验证

从截图中成功识别并计算了12只基金的完整持仓数据：

| 基金名称 | 市值 | 收益 | 最新净值 | 份额 | 成本价 | 成本金额 |
|---------|------|------|---------|------|--------|----------|
| 南方香港优选股票 | 927.11 | 42.73 | 1.8220 | 508.84 | 1.7380 | 884.38 |
| 摩根标普港股通低 | 1923.43 | 209.28 | 1.3424 | 1432.83 | 1.1963 | 1714.15 |
| 华宝纳斯达克精选 | 1409.99 | 90.01 | 2.0665 | 682.31 | 1.9346 | 1319.98 |
| ... | ... | ... | ... | ... | ... | ... |

**计算公式**：
- 份额 = 市值 / 最新净值
- 成本金额 = 市值 - 收益
- 成本价 = 成本金额 / 份额

## 修复方案

### 1. 后端增强 ([ocr_service.py](file:///d:/workdir/code/Explore/fund-tracker/backend/app/services/ocr_service.py))
在 `process_screenshot` 方法中添加：
1. 识别后自动获取最新净值
2. 计算持有份额、成本价、成本金额
3. 返回完整的持仓数据

### 2. 后端API增强 ([ocr.py](file:///d:/workdir/code/Explore/fund-tracker/backend/app/api/v1/ocr.py))
修改 `/extract-positions` 接口，返回计算后的完整数据

### 3. 前端导入优化 ([portfolio.vue](file:///d:/workdir/code/Explore/fund-tracker/frontend/src/pages/portfolio/portfolio.vue))
使用计算后的 `cost_amount` 和 `hold_shares` 导入持仓

## 文件修改清单

1. `backend/app/services/ocr_service.py` - 添加自动计算逻辑
2. `backend/app/api/v1/ocr.py` - 可选，如果需要调整返回格式
3. `frontend/src/pages/portfolio/portfolio.vue` - 优化导入逻辑

请确认后我将实施修复。