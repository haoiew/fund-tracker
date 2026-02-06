# 基金跟踪器 - 系统架构文档

> 版本: v2.0.0  
> 更新日期: 2026-02-06

---

## 目录

1. [系统概述](#系统概述)
2. [整体架构](#整体架构)
3. [数据流架构](#数据流架构)
4. [前端架构](#前端架构)
5. [后端架构](#后端架构)
6. [数据存储](#数据存储)
7. [缓存策略](#缓存策略)
8. [安全设计](#安全设计)

---

## 系统概述

基金跟踪器是一个现代化的基金数据分析平台，采用前后端分离架构，支持多平台部署。系统核心设计理念：

- **高可用性**: 多数据源降级策略确保数据获取
- **高性能**: 多级缓存机制加速数据访问
- **可扩展性**: 模块化设计便于功能扩展
- **用户体验**: 响应式UI和实时数据更新

---

## 整体架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              基金跟踪器系统架构                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                           用户层 (User Layer)                        │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │   Web浏览器   │  │  桌面应用     │  │  移动设备     │              │   │
│  │  │  (Any)       │  │ (Electron)   │  │   (UniApp)   │              │   │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │   │
│  └─────────┼─────────────────┼─────────────────┼──────────────────────┘   │
│            │                 │                 │                          │
│            └─────────────────┼─────────────────┘                          │
│                              │ HTTP/REST                                  │
│  ┌───────────────────────────┼─────────────────────────────────────────┐  │
│  │                      网关层 (Gateway Layer)                          │  │
│  │                    CORS / 限流 / 日志                                 │  │
│  └───────────────────────────┼─────────────────────────────────────────┘  │
│                              │                                            │
│  ┌───────────────────────────┼─────────────────────────────────────────┐  │
│  │                      服务层 (Service Layer)                          │  │
│  │  ┌───────────────────────────────────────────────────────────────┐  │  │
│  │  │                    FastAPI 后端服务                            │  │  │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │  │  │
│  │  │  │ Fund API │ │Portfolio │ │  OCR API │ │  Auth    │        │  │  │
│  │  │  │  基金接口 │ │ 持仓接口  │ │ 识别接口  │ │ 认证接口  │        │  │  │
│  │  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘        │  │  │
│  │  │       └─────────────┴─────────────┴─────────────┘            │  │  │
│  │  │                         │                                   │  │  │
│  │  │  ┌──────────────────────┴──────────────────────┐            │  │  │
│  │  │  │           Services 业务逻辑层               │            │  │  │
│  │  │  │  ┌─────────┐ ┌─────────┐ ┌─────────┐      │            │  │  │
│  │  │  │  │ FundSvc │ │ PortSvc │ │ OcrSvc  │      │            │  │  │
│  │  │  │  └────┬────┘ └────┬────┘ └────┬────┘      │            │  │  │
│  │  │  └───────┼──────────┼──────────┼─────────────┘            │  │  │
│  │  └──────────┼──────────┼──────────┼──────────────────────────┘  │  │
│  └─────────────┼──────────┼──────────┼─────────────────────────────┘  │
│                │          │          │                                 │
│  ┌─────────────┼──────────┼──────────┼─────────────────────────────┐   │
│  │             │    数据层 (Data Layer)                             │   │
│  │  ┌──────────┴──────────┐ ┌────────┴────────┐ ┌──────────────┐  │   │
│  │  │    PostgreSQL       │ │     Redis       │ │ LocalStorage │  │   │
│  │  │    (主数据库)        │ │    (缓存)       │ │  (本地存储)   │  │   │
│  │  │  ┌───────────────┐  │ │  ┌───────────┐  │ │  ┌────────┐  │  │   │
│  │  │  │   funds       │  │ │  │realtime:* │  │ │  │funds   │  │  │   │
│  │  │  │   portfolio   │  │ │  │history:*  │  │ │  │portfolio│  │  │   │
│  │  │  │   users       │  │ │  │search:*   │  │ │  │settings│  │  │   │
│  │  │  └───────────────┘  │ │  └───────────┘  │ │  └────────┘  │  │   │
│  │  └─────────────────────┘ └─────────────────┘ └──────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      外部数据源 (External Sources)                 │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │   │
│  │  │  天天基金     │  │   新浪LOF    │  │   AKShare    │          │   │
│  │  │ 实时估值     │  │  场内行情    │  │  LOF行情     │          │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 数据流架构

### 1. 基金数据获取流程

```
用户请求 ──► API层 ──► Service层 ──► 缓存检查 ──► 数据源获取
                                          │            │
                                          ▼            ▼
                                    返回缓存数据    多数据源降级
                                                        │
                                                        ▼
                                                  天天基金 ──► 新浪LOF ──► AKShare
                                                        │
                                                        ▼
                                                  数据解析 ──► 缓存存储 ──► 返回用户
```

### 2. 持仓管理数据流

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   用户操作   │────►│  Vue组件    │────►│ Pinia Store │────►│ dataManager │
└─────────────┘     └─────────────┘     └─────────────┘     └──────┬──────┘
                                                                   │
                    ┌──────────────────────────────────────────────┘
                    │
                    ▼
            ┌───────────────┐
            │   乐观更新     │◄──── 立即更新UI，提升用户体验
            └───────┬───────┘
                    │
                    ▼
            ┌───────────────┐
            │   API请求      │────► 后端服务
            └───────┬───────┘
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐
   │ 成功回调 │ │ 失败回滚 │ │本地存储 │
   │更新状态  │ │恢复数据  │ │持久化   │
   └─────────┘ └─────────┘ └─────────┘
```

### 3. 图表数据流

```
用户选择时间范围 ──► 组件加载 ──► API请求历史数据
                                        │
                                        ▼
                              ┌─────────────────┐
                              │  request.ts     │
                              │ 响应拦截器解包   │
                              │ data.data ──► data│
                              └────────┬────────┘
                                       │
                                       ▼
                              ┌─────────────────┐
                              │   数据处理       │
                              │ - 日期格式化     │
                              │ - 数值计算       │
                              │ - 涨跌幅计算     │
                              └────────┬────────┘
                                       │
                                       ▼
                              ┌─────────────────┐
                              │  ECharts渲染    │
                              │  (v-show控制)   │
                              └─────────────────┘
```

---

## 前端架构

### 目录结构

```
fund-tracker-desktop/src/
├── api/                    # API接口层
│   ├── request.ts         # Axios封装（含拦截器）
│   ├── fund.ts            # 基金相关API
│   ├── portfolio.ts       # 持仓相关API
│   └── ocr.ts             # OCR相关API
│
├── components/            # 组件层
│   ├── Charts/           # 图表组件
│   │   └── FundChart.vue # 基金走势图
│   ├── FundDetail/       # 基金详情组件
│   │   └── FundDetailDialog.vue
│   └── common/           # 通用组件
│
├── views/                # 页面层
│   ├── Home/            # 首页
│   ├── Portfolio/       # 持仓管理
│   ├── Screen/          # 基金筛选
│   ├── Compare/         # 基金对比
│   └── Settings/        # 设置
│
├── stores/              # 状态管理层
│   ├── dataManager.ts   # 数据管理器（核心）
│   ├── portfolioStore.ts # 持仓状态
│   ├── fundStore.ts     # 基金状态
│   └── settingsStore.ts # 设置状态
│
├── types/               # 类型定义
│   ├── fund.ts          # 基金类型
│   ├── portfolio.ts     # 持仓类型
│   └── api.ts           # API响应类型
│
├── utils/               # 工具函数
│   └── formatters.ts    # 格式化函数
│
├── locales/             # 国际化
│   ├── zh-CN.ts         # 中文
│   └── en-US.ts         # 英文
│
└── router/              # 路由配置
    └── index.ts
```

### 核心模块说明

#### 1. dataManager - 数据管理器

`dataManager` 是前端数据管理的核心，负责统一处理数据的获取、缓存和同步。

**职责**:
- 管理本地存储 (LocalStorage)
- 处理API请求和响应
- 数据去重和合并
- 缓存策略执行

**数据流**:
```typescript
// 1. 组件请求数据
const data = await dataManager.getPortfolio()

// 2. dataManager 检查本地缓存
const cached = localStorage.getItem('portfolio')

// 3. 发起API请求获取最新数据
const response = await portfolioApi.getList()

// 4. 合并数据并去重
const merged = mergeAndDeduplicate(cached, response)

// 5. 更新本地缓存和返回数据
localStorage.setItem('portfolio', merged)
return merged
```

#### 2. request.ts - HTTP请求封装

Axios 封装，包含请求/响应拦截器。

**关键特性**:
- 自动解包 `response.data.data`
- 统一错误处理
- 请求/响应日志
- Token自动添加

```typescript
// 响应拦截器 - 自动解包
responseInterceptor: (response) => {
  const data = response.data
  if (data && typeof data === 'object' && 'code' in data) {
    if (data.code !== 200) {
      return Promise.reject(new Error(data.message || '请求失败'))
    }
    return data.data  // 自动解包
  }
  return data
}
```

#### 3. Pinia Stores

状态管理采用 Pinia，按功能模块划分：

| Store | 职责 | 关键State |
|-------|------|----------|
| portfolioStore | 持仓管理 | portfolio[], summary, loading |
| fundStore | 基金数据 | funds[], realtimeData |
| settingsStore | 应用设置 | language, theme, preferences |

**使用示例**:
```typescript
// 组件中使用
import { usePortfolioStore } from '@/stores/portfolioStore'

const portfolioStore = usePortfolioStore()

// 获取数据
await portfolioStore.refreshPortfolio()

// 访问状态
const items = computed(() => portfolioStore.portfolio)
const totalValue = computed(() => portfolioStore.summary.totalValue)
```

---

## 后端架构

### 目录结构

```
fund-tracker/backend/app/
├── api/                  # API路由层
│   └── v1/
│       ├── fund.py      # 基金接口
│       ├── portfolio.py # 持仓接口
│       └── ocr.py       # OCR接口
│
├── services/            # 业务逻辑层
│   ├── fund_service.py  # 基金服务
│   ├── portfolio_service.py # 持仓服务
│   └── ocr_service.py   # OCR服务
│
├── models/              # 数据模型层
│   ├── fund.py          # 基金模型
│   ├── portfolio.py     # 持仓模型
│   └── user.py          # 用户模型
│
├── schemas/             # Pydantic模型
│   ├── fund.py          # 基金Schema
│   └── portfolio.py     # 持仓Schema
│
├── core/                # 核心配置
│   ├── config.py        # 配置管理
│   └── security.py      # 安全相关
│
└── db/                  # 数据库
    ├── base.py          # 基础模型
    └── session.py       # 会话管理
```

### 多数据源降级策略

为确保数据获取的可靠性，采用多数据源降级策略：

```python
async def get_fund_realtime(code: str):
    """获取基金实时估值，带降级策略"""
    
    # 1. 尝试天天基金
    data = await fetch_from_eastmoney(code)
    if data and data.get('nav'):
        return data
    
    # 2. 降级到新浪LOF
    data = await fetch_from_sina_lof(code)
    if data and data.get('nav'):
        return data
    
    # 3. 降级到AKShare
    data = await fetch_from_akshare(code)
    if data and data.get('nav'):
        return data
    
    # 4. 最终降级到历史净值
    return await get_latest_nav(code)
```

### 缓存策略

采用多级缓存架构：

| 缓存级别 | 存储 | TTL | 用途 |
|---------|------|-----|------|
| L1 | 内存 | 60s | 高频访问数据 |
| L2 | Redis | 5min | 实时估值数据 |
| L3 | Redis | 1h | 历史净值数据 |
| L4 | PostgreSQL | 永久 | 持久化存储 |

---

## 数据存储

### 数据库设计

#### 基金表 (funds)

```sql
CREATE TABLE funds (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) UNIQUE NOT NULL,      -- 基金代码
    name VARCHAR(100) NOT NULL,            -- 基金名称
    type VARCHAR(20),                      -- 基金类型
    manager VARCHAR(50),                   -- 基金经理
    company VARCHAR(100),                  -- 基金公司
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### 持仓表 (portfolio)

```sql
CREATE TABLE portfolio (
    id SERIAL PRIMARY KEY,
    fund_code VARCHAR(10) NOT NULL,        -- 基金代码
    fund_name VARCHAR(100),                -- 基金名称
    shares DECIMAL(15,4),                  -- 持有份额
    cost_nav DECIMAL(10,4),                -- 成本净值
    cost_amount DECIMAL(15,2),             -- 成本金额
    user_id INTEGER,                       -- 用户ID
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### 历史净值表 (fund_nav_history)

```sql
CREATE TABLE fund_nav_history (
    id SERIAL PRIMARY KEY,
    fund_code VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    nav DECIMAL(10,4),                     -- 单位净值
    acc_nav DECIMAL(10,4),                 -- 累计净值
    daily_growth_rate DECIMAL(6,2),        -- 日涨跌幅
    UNIQUE(fund_code, date)
);
```

### 本地存储结构

浏览器 LocalStorage 存储结构：

```typescript
// 基金列表
localStorage.setItem('funds', JSON.stringify({
  data: Fund[],
  timestamp: number,
  version: string
}))

// 持仓数据
localStorage.setItem('portfolio', JSON.stringify({
  data: PortfolioItem[],
  timestamp: number,
  summary: PortfolioSummary
}))

// 用户设置
localStorage.setItem('settings', JSON.stringify({
  language: 'zh-CN',
  theme: 'light',
  defaultTimeRange: '3M'
}))
```

---

## 缓存策略

### 前端缓存

#### LocalStorage 缓存

| 数据类型 | 缓存键 | 过期策略 | 更新时机 |
|---------|--------|---------|---------|
| 基金列表 | `funds` | 1小时 | 手动刷新 |
| 持仓数据 | `portfolio` | 实时 | 操作后更新 |
| 用户设置 | `settings` | 永久 | 修改时更新 |

#### 内存缓存

Vue 组件使用 `computed` 和 `ref` 实现响应式缓存：

```typescript
// 计算属性缓存
const formattedFunds = computed(() => {
  return funds.value.map(fund => ({
    ...fund,
    navFormatted: Number(fund.nav).toFixed(4)
  }))
})
```

### 后端缓存

#### Redis 缓存键设计

```
# 实时估值
realtime:{fund_code}           # TTL: 60s

# 历史净值
history:{fund_code}:{range}    # TTL: 1h

# 搜索结果
search:{keyword}:{page}        # TTL: 10min

# 持仓汇总
portfolio:summary:{user_id}    # TTL: 5min
```

#### 缓存更新策略

1. **主动更新**: 定时任务更新热门基金数据
2. **被动更新**: 用户请求时检查缓存过期
3. **手动刷新**: 用户点击刷新按钮强制更新

---

## 安全设计

### 认证授权

采用 JWT (JSON Web Token) 认证：

```
┌─────────┐                    ┌─────────┐                    ┌─────────┐
│  用户    │─── 登录(用户名/密码) ───►│  后端    │─── 验证 ───►│ 数据库   │
└─────────┘                    └────┬────┘                    └─────────┘
                                    │
                                    ▼ 生成JWT
                              ┌─────────────┐
                              │ Access Token │
                              │ Refresh Token│
                              └──────┬──────┘
                                     │
┌─────────┐                    ┌─────▼─────┐
│  用户    │◄── 返回Token ─────│   后端     │
└────┬────┘                    └───────────┘
     │
     │ 后续请求携带Token
     ▼
┌─────────┐    Authorization: Bearer {token}    ┌─────────┐
│  用户    │────────────────────────────────────►│  后端    │
└─────────┘                                       └────┬────┘
                                                       │
                                                       ▼ 验证Token
                                                 ┌─────────────┐
                                                 │  访问资源    │
                                                 └─────────────┘
```

### 数据安全

1. **密码加密**: 使用 bcrypt 存储密码哈希
2. **SQL注入防护**: 使用 SQLAlchemy ORM，参数化查询
3. **XSS防护**: 前端自动转义输出
4. **CSRF防护**: 使用 SameSite Cookie

### 传输安全

1. **HTTPS**: 生产环境强制 HTTPS
2. **CORS**: 限制允许的域名
3. **HSTS**: 启用 HTTP Strict Transport Security

---

## 性能优化

### 前端优化

1. **代码分割**: 路由懒加载
2. **组件缓存**: 使用 `keep-alive`
3. **虚拟列表**: 长列表使用虚拟滚动
4. **图片优化**: 懒加载、WebP格式

### 后端优化

1. **连接池**: 数据库连接池管理
2. **异步处理**: 使用 async/await
3. **批量查询**: 减少数据库往返
4. **缓存预热**: 定时任务预热热门数据

---

## 监控与日志

### 日志分级

| 级别 | 用途 | 示例 |
|------|------|------|
| DEBUG | 开发调试 | 请求参数、响应数据 |
| INFO | 正常运行 | 请求记录、缓存命中 |
| WARNING | 警告 | 降级到备用数据源 |
| ERROR | 错误 | API请求失败、数据库错误 |

### 监控指标

1. **API响应时间**: P50, P95, P99
2. **缓存命中率**: Redis命中率
3. **错误率**: 5xx错误比例
4. **数据源可用性**: 各数据源成功率

---

## 部署架构

### 开发环境

```
┌─────────────────────────────────────────┐
│           开发机器 (localhost)           │
│  ┌─────────────┐    ┌─────────────┐    │
│  │ 前端开发服务器 │    │ 后端服务     │    │
│  │  localhost  │    │  localhost  │    │
│  │   :5173     │◄──►│   :8001     │    │
│  └─────────────┘    └──────┬──────┘    │
│                            │           │
│  ┌─────────────────────────┴─────────┐ │
│  │        Docker容器                  │ │
│  │  ┌─────────┐      ┌─────────┐    │ │
│  │  │  Redis  │      │PostgreSQL│    │ │
│  │  │  :6379  │      │  :5432  │    │ │
│  │  └─────────┘      └─────────┘    │ │
│  └───────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

### 生产环境

```
┌─────────────────────────────────────────────────────────────┐
│                        负载均衡器 (Nginx)                    │
│                     SSL终止 / 静态资源缓存                    │
└───────────────────────────────┬─────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐      ┌───────────────┐      ┌───────────────┐
│  前端服务器    │      │  后端服务器    │      │  后端服务器    │
│  (CDN/静态)   │      │   (API 1)     │      │   (API 2)     │
└───────────────┘      └───────┬───────┘      └───────┬───────┘
                               │                      │
                               └──────────┬───────────┘
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    │              数据层                        │
                    │  ┌─────────┐  ┌─────────┐  ┌─────────┐   │
                    │  │  Redis  │  │PostgreSQL│  │  备份   │   │
                    │  │ 集群    │  │  主从    │  │  存储   │   │
                    │  └─────────┘  └─────────┘  └─────────┘   │
                    └───────────────────────────────────────────┘
```

---

## 相关文档

- [项目README](../README.md) - 项目概览
- [操作手册](OPERATION_MANUAL.md) - 部署和操作指南
- [前端开发指南](FRONTEND_GUIDE.md) - 前端开发规范
- [故障排查手册](TROUBLESHOOTING.md) - 问题解决方案

---

**Made with ❤️ for investors**
