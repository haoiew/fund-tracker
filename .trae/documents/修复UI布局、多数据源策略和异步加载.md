## 问题分析与修复方案

### 问题1：首页操作面板按钮布局混乱
**解决方案**：
- 将按钮简化为图标展示
- 使用 Tooltip 在鼠标悬停时显示文字信息
- 使用更紧凑的布局

### 问题2：特定基金无法正确加载估值
**涉及基金**：513630、007722、161226、160723、007721、160125、501018
**原因**：这些基金（主要是LOF、QDII）需要特殊数据源

**参考 fund_main.py 的实现**：
- 四级降级策略：天天基金 → 新浪LOF → AKShare LOF → 最新净值
- LOF场内行情（16、50开头）使用新浪接口

**解决方案**：
- 增强后端数据源策略
- 添加更多数据源作为降级

### 问题3：添加更多公开可靠的数据源
**可选数据源**：
1. **雪球** (xueqiu.com) - 基金实时数据
2. **好买基金** (howbuy.com) - 基金净值
3. **基金豆** (funddb.cn) - 基金数据
4. **腾讯财经** - 基金行情
5. **同花顺** (iFinD) - 基金数据
6. **聚宽** (JoinQuant) - 量化数据

### 问题4：异步/并发加载数据源
**解决方案**：
- 使用 `Promise.all()` 或 `Promise.allSettled()` 并发请求多个数据源
- 实现优先级展示逻辑：
  1. 优先展示可靠性高的数据源（天天基金）
  2. 如果主数据源失效或数据落后1小时以上，使用备用数据源
  3. 记录每个数据源的时间戳和可靠性评分

### 问题5：状态图标悬浮展示数据源名称
**解决方案**：
- 在 FundRealtimeData 中添加 data_source 字段
- 使用 ElTooltip 展示数据源信息

### 问题6：持仓管理统计数据更新问题
**问题**：编辑/删除后自动更新的数据不正确，手动刷新后正确
**原因**：乐观更新时计算逻辑与刷新时的计算逻辑不一致

**解决方案**：
- 统一计算逻辑
- 检查 dataManager 中的计算与后端返回的数据差异

## 具体修改计划

### 前端修改
1. **HomeView.vue** - 优化按钮布局为图标+Tooltip
2. **HomeView.vue** - 添加数据源展示Tooltip
3. **dataManager.ts** - 修复统计数据计算逻辑

### 后端修改
1. **fund_core_service.py** - 增强多数据源策略
2. **fund_core_service.py** - 实现并发数据源加载
3. **fund_core_service.py** - 添加更多数据源
4. **schemas/fund.py** - 添加 data_source 和 data_timestamp 字段

## 文件清单

### 前端
- `fund-tracker-desktop/src/views/Home/HomeView.vue`
- `fund-tracker-desktop/src/stores/dataManager.ts`
- `fund-tracker-desktop/src/api/fund.ts`

### 后端
- `fund-tracker/backend/app/services/fund_core_service.py`
- `fund-tracker/backend/app/schemas/fund.py`
- `fund-tracker/backend/app/api/v1/funds.py`