# 更新日志

本文档记录基金跟踪器项目的主要版本更新。

## v3.0.0 (2026-06-04)

### 重大更新

- **架构重构**: 前后端分离，FastAPI + Vue 3 + Electron 架构
- **零依赖部署**: SQLite + 内存缓存，无需 Docker/Redis/PostgreSQL

### 新增功能

- 实时估值查询（多数据源自动降级）
- 历史净值数据与本地持久化
- 持仓管理与实时盈亏计算
- 连续涨跌趋势筛选
- 多基金多周期对比（含基准指数）
- ECharts 可视化图表
- Electron 桌面端应用

### 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.11+ / FastAPI / SQLAlchemy |
| 前端 | Vue 3 / TypeScript / Element Plus / ECharts |
| 桌面端 | Electron |
| 数据库 | SQLite（WAL 模式） |
| 缓存 | 内存 LRU 缓存 |
| 数据源 | efinance + eastmoney 多源降级 + AKShare 备用 |

### 代码质量

- 全量代码质量修复与项目结构精简
- 完善测试框架（pytest + async support）
- ESLint + OxLint 代码规范
- TypeScript 类型检查

---

## v2.1.0

- 命令行可视化和数据源优化

## v2.0.0

- 可读性、数据源和绘图优化

## v1.0.0

- 初始版本
