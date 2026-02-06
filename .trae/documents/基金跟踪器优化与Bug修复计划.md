## 问题分析与修复计划

### 一、问题1：首页基金详情无法显示昨日净值、累计净值、日增长率和绘图

**问题根源：**
1. 后端 `FundRealtimeData` schema 中没有定义 `previous_nav`、`accumulated_nav`、`daily_growth` 字段
2. 后端 `fund_service.py` 的 `get_realtime_data` 方法只获取了估算净值，没有获取昨日净值、累计净值等信息
3. 天天基金API返回的数据中包含这些信息，但没有被提取和返回

**修复方案：**
1. 修改 `fund-tracker/backend/app/schemas/fund.py`，在 `FundRealtimeData` 中添加缺失字段
2. 修改 `fund-tracker/backend/app/services/fund_service.py` 的 `_try_tiantian_fund` 方法，从API响应中提取 `dwjz`（昨日净值）、`ljjz`（累计净值）并计算日增长率
3. 前端 `FundDetailDialog.vue` 已经预留了这些字段的显示，只需确保数据正确传递

---

### 二、问题2：首页添加按钮响应迟钝 + 缺少份额和成本价输入

**问题根源：**
1. `HomeView.vue` 中的 `addToPortfolio` 方法直接调用 API，没有弹出输入对话框
2. 默认使用固定值 `shares = 100`，用户无法自定义
3. 添加操作是同步阻塞的，导致UI卡顿

**修复方案：**
1. 在 `HomeView.vue` 中添加一个对话框组件，包含：
   - 持有份额输入（数字输入框，支持小数）
   - 成本价输入（数字输入框，支持4位小数，默认当前净值）
2. 添加按钮改为打开对话框，用户确认后再执行添加
3. 使用异步操作避免UI阻塞

---

### 三、问题3：添加按钮状态未刷新

**问题根源：**
1. `HomeView.vue` 中没有检查基金是否已在持仓列表中
2. 添加成功后没有更新按钮状态

**修复方案：**
1. 在 `HomeView.vue` 中添加计算属性 `isInPortfolio(code)` 检查基金是否已存在
2. 根据持仓状态动态显示"添加"或"已添加"按钮
3. 使用 `portfolioStore` 的数据实时更新按钮状态

---

### 四、问题4：持仓列表缺少编辑入口

**问题根源：**
1. `PortfolioView.vue` 虽然有编辑按钮，但编辑对话框已经存在
2. 但 `PortfolioView.vue` 的编辑功能已经实现，需要检查是否正常工作

**验证结果：**
- 编辑功能已实现，但需要确保：
  - 持有份额可以编辑
  - 成本价可以编辑
  - 编辑后数据正确保存

---

### 五、问题5：模块间联通性和数据共享

**现状分析：**

| 模块 | 数据共享方式 | 联通性评估 |
|------|-------------|-----------|
| 首页(Home) | fundStore, portfolioStore | ✅ 良好 |
| 持仓管理(Portfolio) | portfolioStore | ✅ 良好 |
| 基金详情(FundDetail) | 通过props接收数据 | ⚠️ 需要改进 |
| 基金筛选(Screen) | fundStore | ✅ 良好 |
| 基金对比(Compare) | fundStore | ✅ 良好 |

**需要改进的地方：**
1. **基金详情弹窗**：当前通过props传递数据，但打开后没有重新获取最新数据
2. **跨模块数据同步**：添加持仓后，首页按钮状态应该自动更新

**改进方案：**
1. 在 `FundDetailDialog.vue` 打开时，重新获取基金实时数据
2. 使用 `portfolioStore` 的响应式数据驱动首页按钮状态

---

## 具体修改文件清单

### 后端修改：
1. `fund-tracker/backend/app/schemas/fund.py` - 添加缺失字段
2. `fund-tracker/backend/app/services/fund_service.py` - 提取完整数据

### 前端修改：
3. `fund-tracker-desktop/src/views/Home/HomeView.vue` - 添加对话框、优化按钮状态
4. `fund-tracker-desktop/src/components/FundDetail/FundDetailDialog.vue` - 确保数据正确显示
5. `fund-tracker-desktop/src/views/Portfolio/PortfolioView.vue` - 验证编辑功能

---

## 预期效果

1. ✅ 基金详情正确显示昨日净值、累计净值、日增长率
2. ✅ 历史走势图正常显示
3. ✅ 添加按钮响应迅速，弹出输入对话框
4. ✅ 可以输入持有份额和成本价
5. ✅ 添加按钮状态根据持仓情况自动刷新
6. ✅ 持仓列表可以编辑持有份额和成本价
7. ✅ 各模块数据共享正常，交互流畅