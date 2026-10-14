# 基金跟踪器 Fund Tracker v3.0

> 现代化的跨端基金跟踪与分析工具

## 项目简介

基金跟踪器是一款专为投资者设计的智能基金分析工具，支持实时估值、历史数据分析、持仓管理、基金筛选与对比等功能。

### 核心特性

- **估值口径**: 天天 H5 优先，缺估值时批量查询新浪；两者无有效估值再采用本地推算，明确标注来源与推算依据
- **持仓管理**: 记录投资金额，实时计算盈亏，支持截图 AI 识别导入
- **基金筛选**: 连续涨跌趋势筛选
- **基金对比**: 多基金多周期对比，含基准指数
- **可视化图表**: ECharts 丰富的图表展示历史走势
- **轻量跨端**: Web 优先，保留 Tauri 桌面与 Android 容器潜力

加载采用本地持仓先返回、源端估值先显示、推算随后补充。空关注列表和持仓列表分别管理；部分基金没有有效估值时仍显示 `--`，不以旧净值补齐。详见[加载耗时、限流与截图问题核查](docs/LOADING_DIAGNOSTICS_20261014.md)。

最新新浪备用源、蓝色“推算”标记、30 样本覆盖与实际 3000 代理计时见[实时估值核查](docs/ESTIMATE_FALLBACK_20261014.md)。接口可用不代表估值准确度或长期 SLA。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + TypeScript + Element Plus + ECharts |
| 运行壳 | Web 优先 / Tauri-ready |
| 后端 | FastAPI + SQLAlchemy |
| 数据库 | SQLite（零外部依赖） |
| 数据源 | 天天 H5 + 新浪估值备用；东方财富/腾讯正式净值；AKShare 用于部分搜索与指数查询 |

## 快速开始

### 环境要求

- Python 3.11+
- Node.js ^20.19.0 || >=22.12.0
- Windows 一键启动脚本默认使用 Miniforge/Conda 环境 `fund-tracker`

### 一键启动（Windows）

```bash
scripts/start.bat
```

### 手动启动

```bash
# 1. 启动后端
cd backend
conda activate fund-tracker
python -m app.main
# 服务地址: http://127.0.0.1:8001
# API文档: http://127.0.0.1:8001/docs

# 2. 启动前端
cd frontend
npm install
npm run dev
# 访问: http://localhost:3000
```

### 跨端运行壳

```bash
cd frontend
npm run tauri:dev:web      # Tauri 预适配 Web 调试，不依赖 Tauri CLI
npm run tauri:build:web    # Tauri 预适配 Web 构建产物
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
├── frontend/          # Vue 3 Web 前端，运行壳保持可替换
│   ├── src/           # Vue 应用源码
└── scripts/           # 启动脚本
```

## 功能模块

### 1. 基金数据模块
- 源端估值优先，缺失时显式推测；无有效推测时显示暂无估值，而不是旧净值或成本价
- 正式净值只在上海时间收盘后且当日已公布时自动显示；首页“数据源”面板可手动选择净值
- API 的 `view=auto/provider/nav` 可明确选择自动、仅源端估值或正式净值，见 [API 说明](docs/API_SPEC.md)
- 历史图表使用单位净值；收益比较链乘来源日增长率，并标注缺失增长率时采用的价格变动口径
- 历史净值数据获取与本地持久化
- 涨跌幅趋势分析
- 基金搜索

### 2. 持仓管理模块
- 添加/删除/更新持仓
- 记录购买金额和份额
- 实时盈亏计算
- 资产分布统计
- AI 识别导入持仓截图，含视觉连通性检测、导入预检和确认导入

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
conda activate fund-tracker
pytest

# 前端 lint
cd frontend
npm run lint
npm run build
```

## 许可

MIT License

数据源实测结果、剩余限制、开源项目候选和智能体/skill 路线见 [2026-10-13 核查报告](docs/DATA_SOURCE_AND_AGENT_PLAN_20261013.md)。本次未安装模型框架、未移植第三方代码，后续选型由用户评估决定。
