## 问题分析

从错误日志中发现以下问题：

### 1. FundDetailDialog.vue - 图表容器未准备好
**原因**：图表容器使用 `v-if="loading"` 和 `v-else` 条件渲染。当 `loading` 为 `true` 时，图表容器不会渲染，所以 `chartRef.value` 是 `undefined`。

### 2. PortfolioView.vue - refreshData 函数调用错误
**原因**：调用 `portfolioStore.refreshData()`，但 portfolioStore 中导出的是 `refreshPortfolio`。

### 3. PortfolioView.vue - toFixed 错误
**原因**：`row.cost_nav` 可能是字符串或 Decimal 类型，不是数字类型。

### 4. Element Plus Radio 警告
**原因**：使用了 `label` 属性，应该使用 `value` 属性。

## 修复方案

### 1. FundDetailDialog.vue
- 修改 `loadHistoryData` 函数，确保图表容器渲染后再初始化图表

### 2. PortfolioView.vue
- 将 `portfolioStore.refreshData()` 改为 `portfolioStore.refreshPortfolio()`
- 修复 `toFixed` 调用，先将值转换为数字

### 3. Radio 组件
- 将所有 `el-radio-button` 的 `label` 改为 `value`

## 涉及文件
1. `d:\workdir\code\Explore\fund-tracker-desktop\src\components\FundDetail\FundDetailDialog.vue`
2. `d:\workdir\code\Explore\fund-tracker-desktop\src\views\Portfolio\PortfolioView.vue`
3. `d:\workdir\code\Explore\fund-tracker-desktop\src\components\Charts\FundChart.vue`
4. `d:\workdir\code\Explore\fund-tracker-desktop\src\views\Screen\ScreenView.vue`
5. `d:\workdir\code\Explore\fund-tracker-desktop\src\views\Compare\CompareView.vue`
6. `d:\workdir\code\Explore\fund-tracker-desktop\src\views\Home\HomeView.vue`
7. `d:\workdir\code\Explore\fund-tracker-desktop\src\views\Settings\SettingsView.vue`

请确认后，我将执行修复。