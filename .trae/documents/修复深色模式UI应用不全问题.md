## 问题分析

从截图中可以看到深色模式下存在以下问题：

1. **基金对比页面** - 背景是白色的，没有应用深色模式
2. **设置页面** - 表单区域背景是白色的，与整体深色主题不协调
3. **Element Plus 组件** - 部分组件没有正确应用深色主题

## 根本原因

1. **缺少 Element Plus 深色模式 CSS 文件** - main.ts 中没有引入 `element-plus/theme-chalk/dark/css-vars.css`
2. **硬编码颜色** - 视图文件中使用了硬编码的浅色颜色值（如 `#fafafa`、`#e5e7eb` 等）
3. **图表样式未适配** - ECharts 图表的 tooltip、坐标轴等样式使用浅色配色

## 修复计划

### 1. 引入 Element Plus 深色模式样式

修改 `main.ts`，添加 Element Plus 深色模式 CSS 文件

### 2. 修复硬编码颜色

修改以下文件中的硬编码颜色为 CSS 变量：

* `CompareView.vue` - 图表容器背景、边框颜色

* `SettingsView.vue` - 表单背景

* `ScreenView.vue` - 检查是否有类似问题

### 3. 修复 ECharts 图表深色模式

修改图表配置，使用 CSS 变量或根据主题动态设置颜色

### 4. 完善全局深色模式样式

在 `global.scss` 中添加更多 Element Plus 组件的深色模式覆盖样式

## 具体修改文件

1. `fund-tracker-desktop/src/main.ts` - 引入深色模式 CSS
2. `fund-tracker-desktop/src/views/Compare/CompareView.vue` - 修复图表和表单样式
3. `fund-tracker-desktop/src/views/Settings/SettingsView.vue` - 修复表单背景
4. \`fund-tracker-desktop/src/styles

