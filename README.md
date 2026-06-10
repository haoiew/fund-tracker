# 基金跟踪器 Fund Tracker v3.0

> 本地化的跨端基金跟踪与分析工具，零外部依赖

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
| 数据源 | efinance + eastmoney 多源降级 + AKShare 备用 |

## 快速开始

```bash
# 一键启动（Windows）
fund-tracker/scripts/start.bat

# 手动启动
cd fund-tracker/backend && pip install -r requirements.txt && python -m app.main
cd fund-tracker/frontend && npm install && npm run dev
```

- 后端: http://127.0.0.1:8001 | API 文档: http://127.0.0.1:8001/docs
- 前端: http://localhost:3000（自动代理 `/api/*` → 后端）

## 功能

- 实时估值查询（多数据源自动降级）
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

## 许可

MIT License
