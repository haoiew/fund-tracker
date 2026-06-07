# 基金跟踪器 v3.0 需求文档

## 项目概述

本地基金跟踪工具，支持实时估值、历史数据、持仓管理、基金筛选和对比。

## 技术栈

| 层 | 技术 | 版本 |
|---|---|---|
| 后端 | Python + FastAPI | 3.11+ / 0.109+ |
| 数据库 | SQLite | 内置 |
| 缓存 | L1内存缓存 | OrderedDict LRU |
| 数据源 | efinance + eastmoney_direct | 已验证100%成功率 |
| 前端 | Vue 3 + Vite + TypeScript | 3.5+ / 7.3+ |
| UI库 | Element Plus | 2.13+ |
| 图表 | ECharts | 5.4+ |
| 运行壳 | Web 优先 / Tauri-ready / Electron兼容 | Vite shell mode |

## 功能需求

### F1 基金列表管理
- 从funds.txt加载基金列表
- 添加/移除基金
- 基金名称自动获取

### F2 实时估值
- efinance批量获取（243ms/21只）
- eastmoney_direct降级（交易时段实时数据）
- QDII基金特殊处理（腾讯API优先）
- 60秒缓存TTL

### F3 历史净值
- 东方财富pingzhongdata为主
- AKShare为备用
- SQLite本地持久化
- 后台异步增量更新

### F4 基金筛选
- 连续上涨/下跌筛选
- 可配置天数和幅度阈值
- 批量处理避免请求过快

### F5 基金对比
- 多基金净值曲线对比
- 支持基准指数（上证、沪深300）
- 多时间周期（1W/1M/3M/6M/1Y/ALL）

### F6 持仓管理
- 持仓CRUD
- 收益计算（实时净值关联）
- 汇总统计

### F7 基金搜索
- 关键词模糊搜索
- 东方财富搜索为主
- AKShare搜索为备用

## 非功能需求

### 启动
- 后端：`python -m app.main`（单命令）
- 前端：`npm run dev`（单命令）
- 一键启动：`scripts/start.bat`
- 无Docker/Redis/PostgreSQL依赖

### 性能
- 实时数据批量获取 < 3秒（21只）
- 图表数据本地缓存命中 < 100ms
- 前端首屏加载 < 2秒

### 未来扩展
- 后端可打包为exe（PyInstaller/Nuitka）
- 前端保持纯 Web 能力，运行时通过 Adapter 适配 Tauri 桌面和未来 Android 容器
- API契约保持稳定（REST，ResponseModel包装）
