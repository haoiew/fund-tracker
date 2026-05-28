# 基金跟踪器 Fund Tracker v3.0

> 现代化的跨端基金跟踪与分析工具

## 项目简介

基金跟踪器是一款专为投资者设计的智能基金分析工具，支持实时估值、历史数据分析、持仓管理、基金筛选与对比等功能。

### 核心特性

- **实时数据**: 多数据源降级策略（efinance + eastmoney），确保数据准确性
- **持仓管理**: 记录投资金额，实时计算盈亏
- **基金筛选**: 连续涨跌趋势筛选
- **基金对比**: 多基金多周期对比，含基准指数
- **可视化图表**: ECharts 丰富的图表展示历史走势
- **桌面应用**: Electron 桌面端，开箱即用

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + TypeScript + Element Plus + ECharts |
| 桌面端 | Electron |
| 后端 | FastAPI + SQLAlchemy |
| 数据库 | SQLite（零外部依赖） |
| 数据源 | efinance + eastmoney API + AKShare |

## 快速开始

### 环境要求

- Python 3.11+
- Node.js ^20.19.0 || >=22.12.0

### 一键启动（Windows）

```bash
scripts/start.bat
```

### 手动启动

```bash
# 1. 启动后端
cd backend
pip install -r requirements.txt
python -m app.main
# 服务地址: http://127.0.0.1:8001
# API文档: http://127.0.0.1:8001/docs

# 2. 启动前端
cd frontend
npm install
npm run dev
# 访问: http://localhost:5173
```

### Electron 桌面端

```bash
cd frontend
npm run electron:dev        # 开发模式
npm run electron:build:win  # 构建 Windows 安装包
```

## 项目结构

```
fund-tracker/
├── backend/           # FastAPI 后端服务
│   ├── app/
│   │   ├── api/v1/    # REST API 路由
│   │   ├── core/      # 数据源、缓存、调度器
│   │   ├── models/    # SQLAlchemy ORM 模型
│   │   ├── schemas/   # Pydantic 数据模型
│   │   └── services/  # 业务逻辑层
│   └── tests/         # pytest 测试
├── frontend/          # Vue 3 + Electron 前端
│   ├── electron/      # Electron 主进程
│   └── src/           # Vue 应用源码
└── scripts/           # 启动脚本
```

## 功能模块

### 1. 基金数据模块
- 实时估值查询（efinance + eastmoney 多源降级）
- 历史净值数据获取与本地持久化
- 涨跌幅趋势分析
- 基金搜索

### 2. 持仓管理模块
- 添加/删除/更新持仓
- 记录购买金额和份额
- 实时盈亏计算
- 资产分布统计

### 3. 基金筛选与对比
- 连续涨跌趋势筛选
- 多基金多周期对比
- 基准指数（上证、沪深300）对比

### 4. 可视化模块
- 净值走势图
- 涨跌幅柱状图
- 资产分布饼图
- 多基金对比图

## 测试

```bash
# 后端测试
cd backend
pip install -r requirements.txt
pytest

# 前端 lint
cd frontend
npm run lint
npm run build
```

## 许可

MIT License
