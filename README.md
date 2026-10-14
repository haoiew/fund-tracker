# 基金跟踪器 Fund Tracker v3.0

> 本地化的跨端基金跟踪与分析工具，无外部数据库/缓存服务依赖；联网数据仍依赖上游服务

## 项目概述

- **fund-tracker/** — 主应用（FastAPI 后端 + Vue 3 前端，预留 Tauri 跨端壳）
- **data-source-test/** — 数据源性能基准测试工具

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.11+ / FastAPI / SQLAlchemy |
| 前端 | Vue 3 / TypeScript / Element Plus / ECharts |
| 运行壳 | Web 优先 / Tauri-ready |
| 数据库 | SQLite（WAL 模式，零外部依赖） |
| 缓存 | 内存 LRU 缓存 |
| 数据源 | 新浪 → 天天 POST → Dayfund → Fund123，并发渐进加载；正式净值与本地推算独立 |

## 快速开始

```bash
# 一键启动（Windows）
fund-tracker/scripts/start.bat

# 手动启动
conda activate fund-tracker
cd fund-tracker/backend
python -m app.main
# 在另一终端，从仓库根目录启动前端
cd fund-tracker/frontend && npm install && npm run dev
```

- 后端: http://127.0.0.1:8001 | API 文档: http://127.0.0.1:8001/docs
- 前端: http://localhost:3000（自动代理 `/api/*` → 后端）

## 功能

- 估值查询：优先源端估值，缺失时显式推测；当日收盘且正式净值已公布才自动切换净值
- 历史净值数据与本地持久化
- 持仓管理与实时盈亏计算
- 连续涨跌趋势筛选
- 多基金多周期对比（含基准指数）
- ECharts 可视化图表

## 测试

```bash
cd fund-tracker/backend && pytest
cd fund-tracker/frontend && npm run lint && npm run build
```

最新新浪估值备用源、界面与实际加载核查见[10-14 实时估值报告](fund-tracker/docs/ESTIMATE_FALLBACK_20261014.md)；架构、开源候选与模型中立规划见[改进方案](fund-tracker/docs/DATA_SOURCE_AND_AGENT_PLAN_20261013.md)。样本可用不代表全市场覆盖、估值精度或持续服务保证。

## 许可

MIT License
