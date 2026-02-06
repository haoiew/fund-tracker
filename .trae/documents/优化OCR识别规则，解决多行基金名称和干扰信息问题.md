## 问题分析

根据图片和OCR识别结果对比，主要问题：

### 1. 多行基金名称未正确合并
- 景顺长城纳斯达克科技ETF联接(QDII)C → 被识别为"定投热基榜 No3" + "克科技ETF联接(.)"
- 天弘标普500发起(QDII-FOF)C → 被识别为"连续跑赢赛道No5" + "(QDII-FOF)C"

### 2. 榜单信息干扰
- "定投热基榜 No3"
- "连续跑赢赛道 No5"
- "商品基金榜 No.l >"
- "领涨先锋 Nol >"

### 3. 基金类型后缀被截断
- (QDII-LOF)、(LOF)A、(QDII-FOF-LOF)等后缀被跳过

## 优化方案

### 1. 增强 `_is_fund_name` 方法
- 添加黑名单过滤榜单信息
- 识别"榜"、"No"、">"等关键词

### 2. 优化 `_parse_position` 方法
- 改进多行基金名称合并逻辑
- 保留基金类型后缀（如QDII-LOF）
- 将后缀附加到基金名称中

### 3. 优化基金名称匹配
- 在匹配基金代码时，清理干扰词
- 使用更智能的相似度计算

## 文件修改

1. `backend/app/services/ocr_service.py`
   - 修改 `_is_fund_name` 方法
   - 修改 `_parse_position` 方法
   - 添加 `_merge_fund_name_lines` 方法

请确认后我将实施修复。