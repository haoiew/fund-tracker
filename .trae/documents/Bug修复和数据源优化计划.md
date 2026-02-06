## 问题分析与修复方案

### 问题2：持仓管理列表不显示数据
**原因分析**：`dataManager.ts` 中的 `getPortfolioWithRealtime` 计算属性会覆盖后端返回的 `current_nav` 等字段，当实时数据不完整时导致显示为0。

**修复方案**：
- 修改 `getPortfolioWithRealtime` 逻辑，优先使用后端已计算好的值
- 只有当实时数据完整且有效时才重新计算

---

### 问题3&4&5：历史净值和基金搜索数据源优化
**当前状态分析**：
- `get_historical_nav` 已经使用 AKShare（`ak.fund_open_fund_info_em`）✅
- `search_funds` 已经使用 AKShare（`ak.fund_name_em`）✅
- 但是 `history_service.py` 中的 `_fetch_and_store` 调用的 `fund_service.get_historical_nav` 可能走不同路径

**修复方案**：
1. 统一历史数据获取路径，确保都使用 AKShare
2. 为 AKShare 调用添加重试机制和错误处理
3. 当 AKShare 失败时，降级到东方财富直接接口
4. 添加请求延迟，避免并发过高导致SSL错误

---

### 问题1：优化关于界面布局
**修复方案**：
- 增加卡片间距（margin-bottom: 24px）
- 优化内边距和行高
- 使布局更加舒展美观

---

## 具体修改文件

### 前端修复
1. `dataManager.ts` - 修复持仓数据显示bug
2. `AboutView.vue` - 优化布局

### 后端修复
1. `history_service.py` - 统一使用 AKShare 获取历史数据
2. `fund_core_service.py` - 添加 AKShare 调用重试机制
3. 添加东方财富降级数据源

---

## 实施步骤

1. **高优先级**：修复持仓显示bug（前端）
2. **高优先级**：历史数据获取优化（后端）
3. **高优先级**：添加重试机制和降级策略（后端）
4. **低优先级**：关于界面美化（前端）