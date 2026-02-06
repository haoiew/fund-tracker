# 基金跟踪器项目集合

> 现代化的跨端基金跟踪与分析工具套件

## 项目概述

本项目包含多个基金跟踪相关的应用程序，满足不同场景的使用需求：

- **fund_core.py** - 核心功能模块，提供基金数据获取、分析和可视化功能
- **fund-tracker** - 完整的 Web 应用（FastAPI 后端 + UniApp 前端）
- **fund-tracker-desktop** - Electron 桌面应用（主要维护版本）

## 项目结构

```
Explore/
├── fund_core.py              # 核心功能模块（独立可用）
├── funds.txt                 # 基金代码列表
├── fund-tracker/            # Web 应用
│   ├── backend/             # FastAPI 后端服务
│   │   ├── app/
│   │   │   ├── api/       # API 路由
│   │   │   ├── services/  # 业务逻辑
│   │   │   ├── models/    # 数据模型
│   │   │   ├── schemas/   # 数据验证
│   │   │   └── config.py  # 配置管理
│   │   ├── tests/          # 测试文件
│   │   └── requirements.txt
│   ├── frontend/            # UniApp 前端
│   │   └── src/
│   │       ├── api/        # API 调用
│   │       ├── pages/       # 页面组件
│   │       └── stores/     # 状态管理
│   └── docker/             # Docker 配置
└── fund-tracker-desktop/    # Electron 桌面应用（主要维护版本）
    ├── electron/            # Electron 主进程
    ├── src/
    │   ├── api/            # API 调用
    │   ├── components/     # Vue 组件
    │   ├── views/          # 页面视图
    │   ├── stores/         # Pinia 状态管理
    │   └── types/          # TypeScript 类型定义
    ├── package.json
    └── vite.config.ts
```

## 系统架构

### 数据流架构

```
┌─────────────────────────────────────────────────────────────┐
│                     基金跟踪器系统架构                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐      HTTP/REST      ┌──────────────────┐ │
│  │              │ ◄─────────────────► │                  │ │
│  │   桌面端      │    Axios请求        │   FastAPI后端     │ │
│  │  (Vue3+      │                     │  (Python)        │ │
│  │   Electron)  │                     │                  │ │
│  │              │    ┌──────────┐     │  ┌────────────┐  │ │
│  │ ┌──────────┐ │    │  Pinia   │     │  │  Services  │  │ │
│  │ │  Views   │ │◄───┤  Stores  │     │  │  (业务逻辑) │  │ │
│  │ │ (页面)   │ │    │ (状态管理)│     │  └─────┬──────┘  │ │
│  │ └────┬─────┘ │    └────┬─────┘     │        │         │ │
│  │      │       │         │           │  ┌─────▼──────┐  │ │
│  │ ┌────▼─────┐ │    ┌────▼─────┐     │  │  Models    │  │ │
│  │ │Components│ │    │dataManager     │  │ (SQLAlchemy)│  │ │
│  │ │(组件)    │ │    │(数据管理器)│     │  └─────┬──────┘  │ │
│  │ └────┬─────┘ │    └────┬─────┘     │        │         │ │
│  │      │       │         │           │  ┌─────▼──────┐  │ │
│  │ ┌────▼─────┐ │    ┌────▼─────┐     │  │ PostgreSQL │  │ │
│  │ │  ECharts │ │    │ LocalStorage    │  │  (主数据库) │  │ │
│  │ │ (图表)   │ │    │(本地缓存) │     │  └────────────┘  │ │
│  │ └──────────┘ │    └──────────┘     │                  │ │
│  │              │                     │  ┌────────────┐  │ │
│  │              │                     │  │   Redis    │  │ │
│  │              │                     │  │  (缓存)    │  │ │
│  └──────────────┘                     │  └────────────┘  │ │
│                                       └──────────────────┘ │
│                                                             │
│  外部数据源: 天天基金 / 新浪LOF / AKShare                    │
└─────────────────────────────────────────────────────────────┘
```

### 核心数据流

1. **API 请求流程**：
   ```
   组件调用 → api/ 模块 → request.ts (Axios) → FastAPI后端 → 返回数据
   ```
   - 注意：`request.ts` 中的响应拦截器会自动解包 `response.data.data`，所以组件中直接获取 `response.data` 即可

2. **状态管理流程**：
   ```
   组件 → Pinia Store → dataManager → API / LocalStorage
   ```
   - `dataManager` 统一管理数据获取和缓存策略
   - 支持乐观更新，提升用户体验

3. **图表渲染流程**：
   ```
   数据获取 → 数据处理 → ECharts初始化 → 图表渲染
   ```
   - 使用 `v-show` 而非 `v-if` 确保图表容器始终存在于 DOM

## 快速开始

### 方式一：使用核心模块（命令行）

直接运行核心模块，适合快速查看基金数据：

```bash
# 确保安装了依赖
pip install pandas akshare matplotlib rich requests

# 运行核心模块
python fund_core.py
```

### 方式二：Web 应用

启动完整的 Web 应用，支持更多功能：

```bash
# 1. 启动后端
cd fund-tracker/backend
pip install -r requirements.txt
python -m app.main

# 2. 启动前端（新终端）
cd fund-tracker/frontend
npm install
npm run dev:h5
```

访问 http://localhost:8000/docs 查看 API 文档

### 方式三：桌面应用（推荐）

启动桌面应用，提供最佳用户体验：

```bash
cd fund-tracker-desktop
npm install
npm run dev
```

桌面应用特性：
- 原生桌面体验
- 离线数据缓存
- 丰富的图表展示
- 多语言支持（中英文）
- 现代化 UI 设计

## 功能特性

### 核心功能（fund_core.py）

- 📊 实时估值查询（多数据源降级策略）
- 📈 历史净值数据获取
- 🔍 涨跌幅趋势分析
- 📉 基金筛选（连续上涨/下跌）
- 🎨 数据可视化（matplotlib 图表）

### Web 应用（fund-tracker）

- 🚀 跨端支持（H5、微信小程序、Android App）
- 💰 持仓管理（记录投资金额，实时计算盈亏）
- 📸 OCR 识别（截图自动识别基金代码）
- 🤖 智能分析（AI 驱动的投资建议）
- 🔐 用户认证（JWT 令牌）

### 桌面应用（fund-tracker-desktop）

- 🖥️ 原生桌面体验
- 🌐 离线数据缓存（LocalStorage）
- 📊 丰富的图表展示（ECharts）
- 🌍 多语言支持（vue-i18n）
- 🎨 现代化 UI 设计（Element Plus）
- 🔄 实时数据更新
- 📈 基金对比分析
- 🔍 智能基金筛选

## 技术栈

| 项目 | 后端 | 前端 | 数据库 | 缓存 |
|------|------|------|--------|------|
| 核心模块 | Python | - | - | - |
| Web 应用 | FastAPI + SQLAlchemy | UniApp + Vue 3 | SQLite / PostgreSQL | Redis |
| 桌面应用 | FastAPI | Vue 3 + Electron + TypeScript | PostgreSQL | Redis + LocalStorage |

### 前端技术栈详情

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue.js | 3.4+ | 前端框架 |
| TypeScript | 5.3+ | 类型系统 |
| Vite | 5.0+ | 构建工具 |
| Element Plus | 2.5+ | UI组件库 |
| Pinia | 2.1+ | 状态管理 |
| Vue Router | 4.2+ | 路由管理 |
| Axios | 1.6+ | HTTP客户端 |
| ECharts | 5.4+ | 图表库 |
| vue-i18n | 9.x | 国际化 |

## 配置说明

### 统一配置模块

项目使用 `shared/config.py` 作为统一配置管理，支持跨项目共享配置。

**配置类**:
- `BaseConfig` - 基础配置类
- `FundConfig` - 基金数据配置
- `ChartConfig` - 图表配置
- `PlotConfig` - 绘图配置
- `ServerConfig` - 服务器配置
- `OcrConfig` - OCR 配置

**使用方式**:
```python
# 方式一：使用配置对象
from shared import get_fund_config
fund_config = get_fund_config()
print(fund_config.DEFAULT_FUNDS)

# 方式二：使用向后兼容的 CONFIG 字典
from shared import CONFIG
print(CONFIG["default_funds"])
```

详细文档请参考 [shared/README.md](shared/README.md)

### 核心模块配置

编辑 `fund_core.py` 中的 `CONFIG` 字典（或使用环境变量）：

```python
# 从 shared 模块导入的配置
CONFIG = {
    "file_path": "funds.txt",           # 基金代码文件
    "default_funds": [...],             # 默认基金列表
    "screen_up": {"days": 2, "pct": 0.03},   # 上涨筛选条件
    "screen_down": {"days": 3, "pct": 0.03}, # 下跌筛选条件
    "plot_mode": 0,                      # 绘图模式（0-不绘图，1-对比图，2-子图）
    "plot_range": "1W",                  # 时间范围
}
```

### Web 应用配置

复制 `fund-tracker/backend/.env.example` 为 `.env` 并修改：

```env
# 服务器配置
HOST=0.0.0.0
PORT=8001
DEBUG=false

# CORS 配置
CORS_ORIGINS=http://localhost:5173,http://localhost:8000

# 数据库配置
DATABASE_URL=sqlite:///./fundtracker.db

# Redis 配置
REDIS_URL=redis://localhost:6379/0

# JWT 配置（生产环境必须设置）
SECRET_KEY=your-secret-key-here

# 微信配置
WECHAT_APPID=your-appid
WECHAT_SECRET=your-secret
```

### 桌面应用配置

编辑 `fund-tracker-desktop/.env.development`：

```env
# API 配置
VITE_API_BASE_URL=http://localhost:8001/api/v1

# 应用配置
VITE_APP_TITLE=基金跟踪器
VITE_APP_VERSION=2.0.0
```

## 开发指南

### 添加新功能

1. **核心模块**：在 `fund_core.py` 中添加新方法
2. **Web 后端**：在 `fund-tracker/backend/app/services/` 中添加服务层，在 `api/v1/` 中添加路由
3. **Web 前端**：在 `fund-tracker/frontend/src/pages/` 中添加页面，在 `api/` 中添加 API 调用
4. **桌面应用**：在 `fund-tracker-desktop/src/views/` 中添加视图，在 `api/` 中添加 API 调用

### 前端开发规范

#### API 调用规范

```typescript
// api/fund.ts
import request from './request'

export const fundApi = {
  // 获取基金列表
  getList: () => request.get('/funds'),
  
  // 获取基金详情（注意：response.data 已经是解包后的数据）
  getDetail: (code: string) => request.get(`/funds/${code}`),
  
  // 获取历史数据
  getHistory: (code: string, range: string) => 
    request.get(`/funds/${code}/history`, { params: { range } })
}
```

#### 状态管理规范

```typescript
// stores/fundStore.ts
import { defineStore } from 'pinia'
import { fundApi } from '@/api/fund'

export const useFundStore = defineStore('fund', {
  state: () => ({
    funds: [] as Fund[],
    loading: false
  }),
  
  actions: {
    async fetchFunds() {
      this.loading = true
      try {
        const data = await fundApi.getList()
        this.funds = data
      } finally {
        this.loading = false
      }
    }
  }
})
```

#### 组件开发规范

```vue
<!-- components/FundCard.vue -->
<template>
  <div class="fund-card">
    <h3>{{ fund.name }}</h3>
    <p>净值: {{ formatNav(fund.nav) }}</p>
  </div>
</template>

<script setup lang="ts">
import type { Fund } from '@/types/fund'

interface Props {
  fund: Fund
}

defineProps<Props>()

const formatNav = (nav: number | string) => {
  return Number(nav || 0).toFixed(4)
}
</script>
```

### 运行测试

```bash
# 后端测试
cd fund-tracker/backend
pytest

# 前端测试（需要配置）
cd fund-tracker-desktop
npm run test
```

## API 文档

Web 应用提供完整的 API 文档：

- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

### 重要说明：API 响应数据处理

项目使用了 Axios 响应拦截器自动解包数据：

```typescript
// request.ts 中的响应拦截器
responseInterceptor: (response) => {
  const data = response.data
  if (data && typeof data === 'object' && 'code' in data) {
    if (data.code !== 200) {
      return Promise.reject(new Error(data.message || '请求失败'))
    }
    return data.data  // 自动解包，返回 data.data
  }
  return data
}
```

这意味着：
- ✅ 正确：`const data = await fundApi.getHistory(code)` 直接使用 `data`
- ❌ 错误：`const data = await fundApi.getHistory(code).then(r => r.data)` 会导致双重解包

## 常见问题

### Q: 如何添加新的基金代码？

A: 编辑 `funds.txt` 文件，每行一个基金代码（6位数字）

### Q: 数据来源有哪些？

A: 支持多数据源降级策略：
1. 天天基金（实时估值）
2. 新浪 LOF（场内行情）
3. AKShare（LOF 实时行情）
4. 最新净值（历史数据）

### Q: 如何部署到生产环境？

A: 
- **Web 应用**：使用 Docker 部署，参考 `fund-tracker/docker/` 目录
- **桌面应用**：运行 `npm run electron:build` 打包安装包

### Q: 图表不显示怎么办？

A: 检查以下几点：
1. 确保使用 `v-show` 而非 `v-if` 控制图表容器显示
2. 确保图表容器有明确的宽高
3. 检查浏览器控制台是否有 ECharts 相关错误

### Q: 如何处理 Decimal 类型的数值？

A: 后端返回的 Decimal 类型需要转换为 Number：
```typescript
// ✅ 正确
const value = Number(row.cost_nav || 0).toFixed(4)

// ❌ 错误（cost_nav 可能是 Decimal 字符串）
const value = row.cost_nav.toFixed(4)
```

## 相关文档

- [操作手册](docs/OPERATION_MANUAL.md) - 详细的部署和操作指南
- [架构文档](docs/ARCHITECTURE.md) - 系统架构和数据流说明
- [前端开发指南](docs/FRONTEND_GUIDE.md) - 前端开发规范和最佳实践
- [故障排查](docs/TROUBLESHOOTING.md) - 常见问题解决方案

## 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

MIT License

## 联系方式

如有问题或建议，请提交 Issue。

---

Made with ❤️ for investors
