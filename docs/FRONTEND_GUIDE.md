# 基金跟踪器 - 前端开发指南

> 版本: v2.0.0  
> 更新日期: 2026-02-06

---

## 目录

1. [项目概述](#项目概述)
2. [开发环境配置](#开发环境配置)
3. [项目结构](#项目结构)
4. [开发规范](#开发规范)
5. [状态管理](#状态管理)
6. [API调用](#api调用)
7. [组件开发](#组件开发)
8. [类型定义](#类型定义)
9. [国际化](#国际化)
10. [常见问题](#常见问题)

---

## 项目概述

基金跟踪器桌面端采用 Vue 3 + TypeScript + Electron 技术栈，提供现代化的基金数据分析体验。

### 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue.js | 3.4+ | 前端框架 |
| TypeScript | 5.3+ | 类型系统 |
| Electron | 28+ | 桌面应用框架 |
| Vite | 5.0+ | 构建工具 |
| Element Plus | 2.5+ | UI组件库 |
| Pinia | 2.1+ | 状态管理 |
| Vue Router | 4.2+ | 路由管理 |
| Axios | 1.6+ | HTTP客户端 |
| ECharts | 5.4+ | 图表库 |
| vue-i18n | 9.x | 国际化 |

---

## 开发环境配置

### 1. 安装 Node.js

```bash
# 使用 nvm 安装（推荐）
nvm install 18
nvm use 18

# 验证安装
node -v  # v18.x.x
npm -v   # 9.x.x
```

### 2. 安装依赖

```bash
cd fund-tracker-desktop
npm install
```

### 3. 配置环境变量

创建 `.env.local` 文件：

```env
# API配置
VITE_API_BASE_URL=http://localhost:8001/api/v1

# 应用配置
VITE_APP_TITLE=基金跟踪器
VITE_APP_VERSION=2.0.0
```

### 4. 启动开发服务器

```bash
# 开发模式
npm run dev

# Electron模式
npm run electron:dev
```

---

## 项目结构

```
fund-tracker-desktop/src/
├── api/                    # API接口层
│   ├── request.ts         # Axios封装
│   ├── fund.ts            # 基金API
│   ├── portfolio.ts       # 持仓API
│   └── ocr.ts             # OCR API
│
├── components/            # 组件层
│   ├── Charts/           # 图表组件
│   ├── FundDetail/       # 基金详情
│   └── common/           # 通用组件
│
├── views/                # 页面层
│   ├── Home/            # 首页
│   ├── Portfolio/       # 持仓管理
│   ├── Screen/          # 基金筛选
│   ├── Compare/         # 基金对比
│   └── Settings/        # 设置
│
├── stores/              # 状态管理
│   ├── dataManager.ts   # 数据管理器
│   ├── portfolioStore.ts
│   ├── fundStore.ts
│   └── settingsStore.ts
│
├── types/               # 类型定义
│   ├── fund.ts
│   ├── portfolio.ts
│   └── api.ts
│
├── utils/               # 工具函数
│   └── formatters.ts
│
├── locales/             # 国际化
│   ├── zh-CN.ts
│   └── en-US.ts
│
├── router/              # 路由
│   └── index.ts
│
├── App.vue              # 根组件
└── main.ts              # 入口文件
```

---

## 开发规范

### 命名规范

| 类型 | 命名方式 | 示例 |
|------|----------|------|
| 组件 | PascalCase | `FundCard.vue`, `FundDetailDialog.vue` |
| 组合式函数 | camelCase | `useFundData.ts`, `useChart.ts` |
| Store | camelCase | `portfolioStore.ts`, `fundStore.ts` |
| 类型 | PascalCase | `Fund`, `PortfolioItem`, `ApiResponse` |
| 常量 | SCREAMING_SNAKE_CASE | `DEFAULT_FUNDS`, `CACHE_TTL` |
| 枚举 | PascalCase | `FundType`, `TimeRange` |

### 文件组织规范

```
ComponentName/
├── index.vue           # 主组件
├── types.ts           # 组件类型（可选）
├── utils.ts           # 组件工具函数（可选）
└── components/        # 子组件（可选）
    └── SubComponent.vue
```

### Vue 组件规范

#### 单文件组件结构

```vue
<template>
  <!-- 模板 -->
</template>

<script setup lang="ts">
// 1. 导入（按类型分组）
import { ref, computed, onMounted } from 'vue'
import type { Fund } from '@/types/fund'

// 2. 类型定义
interface Props {
  fund: Fund
  showDetail?: boolean
}

// 3. Props & Emits
const props = withDefaults(defineProps<Props>(), {
  showDetail: false
})

const emit = defineEmits<{
  click: [fund: Fund]
  update: [value: string]
}>()

// 4. 响应式数据
const loading = ref(false)
const data = ref<Fund[]>([])

// 5. 计算属性
const formattedData = computed(() => {
  return data.value.map(item => ({
    ...item,
    navFormatted: formatNav(item.nav)
  }))
})

// 6. 方法
const handleClick = (fund: Fund) => {
  emit('click', fund)
}

// 7. 生命周期
onMounted(() => {
  loadData()
})
</script>

<style scoped>
/* 样式 */
</style>
```

### TypeScript 规范

#### 类型定义

```typescript
// types/fund.ts

// 基础类型
export interface Fund {
  id: number
  code: string
  name: string
  nav: number | string  // 后端可能返回 Decimal 字符串
  accNav: number
  dailyGrowthRate: number
  updateTime: string
}

// 枚举类型
export enum TimeRange {
  ONE_WEEK = '1W',
  ONE_MONTH = '1M',
  THREE_MONTHS = '3M',
  SIX_MONTHS = '6M',
  ONE_YEAR = '1Y',
  THREE_YEARS = '3Y'
}

// 联合类型
export type FundType = 'stock' | 'bond' | 'hybrid' | 'index' | 'qdii'

// 工具类型
export type FundList = Fund[]
export type FundMap = Map<string, Fund>
```

#### 严格类型检查

```typescript
// ✅ 正确 - 明确类型
const fundList = ref<Fund[]>([])
const currentFund = ref<Fund | null>(null)

// ❌ 错误 - 隐式 any
const fundList = ref([])
const currentFund = ref(null)
```

---

## 状态管理

### Pinia Store 规范

#### Store 结构

```typescript
// stores/fundStore.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Fund } from '@/types/fund'
import { fundApi } from '@/api/fund'

export const useFundStore = defineStore('fund', () => {
  // ============ State ============
  const funds = ref<Fund[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  
  // ============ Getters ============
  const fundCount = computed(() => funds.value.length)
  
  const fundMap = computed(() => {
    const map = new Map<string, Fund>()
    funds.value.forEach(fund => map.set(fund.code, fund))
    return map
  })
  
  // ============ Actions ============
  async function fetchFunds() {
    loading.value = true
    error.value = null
    
    try {
      const data = await fundApi.getList()
      funds.value = data
    } catch (err) {
      error.value = err instanceof Error ? err.message : '获取失败'
      throw err
    } finally {
      loading.value = false
    }
  }
  
  function getFundByCode(code: string): Fund | undefined {
    return fundMap.value.get(code)
  }
  
  // ============ Return ============
  return {
    // State
    funds,
    loading,
    error,
    // Getters
    fundCount,
    fundMap,
    // Actions
    fetchFunds,
    getFundByCode
  }
})
```

#### Store 使用

```vue
<script setup lang="ts">
import { useFundStore } from '@/stores/fundStore'
import { storeToRefs } from 'pinia'

const fundStore = useFundStore()

// 使用 storeToRefs 保持响应性
const { funds, loading } = storeToRefs(fundStore)

// 方法直接解构
const { fetchFunds } = fundStore

// 组件挂载时获取数据
onMounted(() => {
  fetchFunds()
})
</script>
```

### dataManager - 数据管理器

`dataManager` 是核心数据管理模块，统一处理数据的获取、缓存和同步。

#### 核心功能

```typescript
// stores/dataManager.ts

export const dataManager = {
  // 获取持仓数据（带缓存）
  async getPortfolio(): Promise<PortfolioItem[]> {
    // 1. 检查本地缓存
    const cached = this.getFromLocalStorage('portfolio')
    
    // 2. 发起API请求
    try {
      const response = await portfolioApi.getList()
      
      // 3. 数据去重
      const uniqueData = this.deduplicate(response)
      
      // 4. 更新本地缓存
      this.saveToLocalStorage('portfolio', uniqueData)
      
      return uniqueData
    } catch (error) {
      // 5. 失败时返回缓存数据
      return cached || []
    }
  },
  
  // 数据去重
  deduplicate<T extends { id?: number }>(items: T[]): T[] {
    const map = new Map<number, T>()
    items.forEach(item => {
      if (item.id !== undefined) {
        map.set(item.id, item)
      }
    })
    return Array.from(map.values())
  },
  
  // 本地存储操作
  saveToLocalStorage(key: string, data: any) {
    localStorage.setItem(key, JSON.stringify({
      data,
      timestamp: Date.now()
    }))
  },
  
  getFromLocalStorage(key: string): any | null {
    const stored = localStorage.getItem(key)
    if (!stored) return null
    
    try {
      const parsed = JSON.parse(stored)
      // 检查过期时间（1小时）
      if (Date.now() - parsed.timestamp > 3600000) {
        localStorage.removeItem(key)
        return null
      }
      return parsed.data
    } catch {
      return null
    }
  }
}
```

---

## API调用

### request.ts - HTTP请求封装

```typescript
// api/request.ts
import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
request.interceptors.request.use(
  (config) => {
    // 添加认证Token
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器 - 关键：自动解包 data.data
request.interceptors.response.use(
  (response) => {
    const data = response.data
    
    // 统一响应格式处理
    if (data && typeof data === 'object' && 'code' in data) {
      if (data.code !== 200) {
        ElMessage.error(data.message || '请求失败')
        return Promise.reject(new Error(data.message))
      }
      return data.data  // 自动解包
    }
    
    return data
  },
  (error) => {
    const message = error.response?.data?.message || '网络错误'
    ElMessage.error(message)
    return Promise.reject(error)
  }
)

export default request
```

### API 模块定义

```typescript
// api/fund.ts
import request from './request'
import type { Fund, FundChartData } from '@/types/fund'

export const fundApi = {
  // 获取基金列表
  getList(): Promise<Fund[]> {
    return request.get('/funds')
  },
  
  // 获取基金详情
  getDetail(code: string): Promise<Fund> {
    return request.get(`/funds/${code}`)
  },
  
  // 获取历史数据
  getHistory(code: string, range: string): Promise<FundChartData> {
    return request.get(`/funds/${code}/history`, {
      params: { range }
    })
  },
  
  // 批量获取实时估值
  getRealtimeBatch(codes: string[]): Promise<Record<string, Fund>> {
    return request.post('/funds/realtime/batch', { codes })
  }
}
```

### API 调用最佳实践

```typescript
// ✅ 正确 - 直接使用返回数据
const data = await fundApi.getHistory(code, range)
console.log(data.dates)  // data 已经是解包后的数据

// ❌ 错误 - 双重解包
const response = await fundApi.getHistory(code, range)
const data = response.data  // 错误！data 不存在
```

---

## 组件开发

### 基础组件示例

```vue
<!-- components/FundCard.vue -->
<template>
  <el-card class="fund-card" :class="{ 'is-up': isUp, 'is-down': isDown }">
    <div class="fund-header">
      <h4 class="fund-name">{{ fund.name }}</h4>
      <span class="fund-code">{{ fund.code }}</span>
    </div>
    
    <div class="fund-data">
      <div class="nav-section">
        <span class="label">净值</span>
        <span class="value" :class="growthClass">
          {{ formatNav(fund.nav) }}
        </span>
      </div>
      
      <div class="growth-section">
        <span class="label">日涨跌</span>
        <span class="value" :class="growthClass">
          {{ formatGrowthRate(fund.dailyGrowthRate) }}
        </span>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Fund } from '@/types/fund'
import { formatNav, formatGrowthRate } from '@/utils/formatters'

interface Props {
  fund: Fund
}

const props = defineProps<Props>()

const isUp = computed(() => (props.fund.dailyGrowthRate || 0) > 0)
const isDown = computed(() => (props.fund.dailyGrowthRate || 0) < 0)

const growthClass = computed(() => ({
  'text-up': isUp.value,
  'text-down': isDown.value,
  'text-neutral': !isUp.value && !isDown.value
}))
</script>

<style scoped>
.fund-card {
  margin-bottom: 12px;
  transition: all 0.3s;
}

.fund-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.fund-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.fund-name {
  margin: 0;
  font-size: 16px;
}

.fund-code {
  color: #999;
  font-size: 12px;
}

.fund-data {
  display: flex;
  justify-content: space-between;
}

.text-up { color: #f56c6c; }
.text-down { color: #67c23a; }
.text-neutral { color: #909399; }
</style>
```

### 图表组件开发

```vue
<!-- components/Charts/FundChart.vue -->
<template>
  <div class="chart-wrapper">
    <!-- 使用 v-show 而非 v-if，确保容器始终存在 -->
    <div v-show="loading" class="chart-loading">
      <el-skeleton :rows="5" animated />
    </div>
    <div v-show="!loading" ref="chartRef" class="chart-container"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import type { FundChartData } from '@/types/fund'
import { fundApi } from '@/api/fund'

interface Props {
  code: string
  timeRange?: string
}

const props = withDefaults(defineProps<Props>(), {
  timeRange: '3M'
})

const chartRef = ref<HTMLDivElement>()
const loading = ref(false)
let chart: echarts.ECharts | null = null

// 初始化图表
const initChart = () => {
  if (!chartRef.value) return
  
  chart = echarts.init(chartRef.value)
  
  // 响应式
  const resizeHandler = () => chart?.resize()
  window.addEventListener('resize', resizeHandler)
  
  onUnmounted(() => {
    window.removeEventListener('resize', resizeHandler)
    chart?.dispose()
  })
}

// 加载数据
const loadData = async () => {
  loading.value = true
  
  try {
    const data = await fundApi.getHistory(props.code, props.timeRange)
    
    if (!data || !Array.isArray(data.dates) || data.dates.length === 0) {
      console.warn('图表数据为空')
      return
    }
    
    updateChart(data)
  } catch (error) {
    console.error('加载图表数据失败:', error)
  } finally {
    loading.value = false
  }
}

// 更新图表
const updateChart = (data: FundChartData) => {
  if (!chart) return
  
  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'axis'
    },
    xAxis: {
      type: 'category',
      data: data.dates
    },
    yAxis: {
      type: 'value',
      scale: true
    },
    series: [{
      type: 'line',
      data: data.navs,
      smooth: true,
      symbol: 'none'
    }]
  }
  
  chart.setOption(option)
}

// 监听属性变化
watch(() => props.timeRange, loadData)
watch(() => props.code, loadData)

onMounted(() => {
  initChart()
  loadData()
})
</script>

<style scoped>
.chart-wrapper {
  width: 100%;
  height: 400px;
}

.chart-container {
  width: 100%;
  height: 100%;
}

.chart-loading {
  padding: 20px;
}
</style>
```

---

## 类型定义

### 基金相关类型

```typescript
// types/fund.ts

/** 基金基础信息 */
export interface Fund {
  id: number
  code: string           // 基金代码，6位数字
  name: string           // 基金名称
  type: FundType         // 基金类型
  nav: number | string   // 单位净值（后端可能返回Decimal字符串）
  accNav: number         // 累计净值
  dailyGrowthRate: number  // 日涨跌幅
  updateTime: string     // 更新时间
}

/** 基金类型 */
export type FundType = 'stock' | 'bond' | 'hybrid' | 'index' | 'qdii' | 'money'

/** 基金图表数据 */
export interface FundChartData {
  dates: string[]        // 日期数组
  navs: number[]         // 净值数组
  accNavs: number[]      // 累计净值数组
  growthRates: number[]  // 涨跌幅数组
}

/** 基金筛选条件 */
export interface FundScreenCriteria {
  type?: FundType
  minNav?: number
  maxNav?: number
  growthRange?: TimeRange
  minGrowth?: number
  maxGrowth?: number
}

/** 时间范围 */
export enum TimeRange {
  ONE_WEEK = '1W',
  ONE_MONTH = '1M',
  THREE_MONTHS = '3M',
  SIX_MONTHS = '6M',
  ONE_YEAR = '1Y',
  THREE_YEARS = '3Y',
  ALL = 'ALL'
}
```

### 持仓相关类型

```typescript
// types/portfolio.ts

/** 持仓项 */
export interface PortfolioItem {
  id: number
  fundCode: string       // 基金代码
  fundName: string       // 基金名称
  shares: number | string // 持有份额（Decimal）
  costNav: number | string // 成本净值（Decimal）
  costAmount: number | string // 成本金额（Decimal）
  currentNav?: number    // 当前净值
  marketValue?: number   // 市值
  profit?: number        // 盈亏金额
  profitRate?: number    // 盈亏率
  createdAt: string
  updatedAt: string
}

/** 持仓汇总 */
export interface PortfolioSummary {
  totalCost: number      // 总成本
  totalMarketValue: number // 总市值
  totalProfit: number    // 总盈亏
  totalProfitRate: number // 总盈亏率
  fundCount: number      // 基金数量
}

/** 持仓操作类型 */
export type PortfolioOperation = 'add' | 'update' | 'delete'
```

### API 响应类型

```typescript
// types/api.ts

/** 标准API响应 */
export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

/** 分页响应 */
export interface PaginatedResponse<T> {
  list: T[]
  total: number
  page: number
  pageSize: number
}

/** API错误 */
export interface ApiError {
  code: number
  message: string
  details?: Record<string, string[]>
}
```

---

## 国际化

### 配置

```typescript
// locales/index.ts
import { createI18n } from 'vue-i18n'
import zhCN from './zh-CN'
import enUS from './en-US'

const i18n = createI18n({
  legacy: false,
  locale: localStorage.getItem('language') || 'zh-CN',
  fallbackLocale: 'zh-CN',
  messages: {
    'zh-CN': zhCN,
    'en-US': enUS
  }
})

export default i18n
```

### 语言文件

```typescript
// locales/zh-CN.ts
export default {
  common: {
    confirm: '确认',
    cancel: '取消',
    save: '保存',
    delete: '删除',
    edit: '编辑',
    loading: '加载中...',
    success: '操作成功',
    error: '操作失败'
  },
  fund: {
    name: '基金名称',
    code: '基金代码',
    nav: '单位净值',
    growth: '涨跌幅',
    search: '搜索基金',
    addToPortfolio: '加入持仓'
  },
  portfolio: {
    title: '我的持仓',
    totalValue: '总市值',
    totalProfit: '总盈亏',
    profitRate: '收益率',
    addPosition: '添加持仓'
  }
}
```

### 使用

```vue
<template>
  <div>
    <h1>{{ $t('portfolio.title') }}</h1>
    <el-button>{{ $t('common.save') }}</el-button>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t, locale } = useI18n()

// 切换语言
const switchLanguage = (lang: string) => {
  locale.value = lang
  localStorage.setItem('language', lang)
}
</script>
```

---

## 常见问题

### Q1: 图表不显示或报错 "容器未准备好"

**原因**: 使用 `v-if` 控制图表容器，导致 ECharts 初始化时容器不存在

**解决**:
```vue
<!-- ❌ 错误 -->
<div v-if="!loading" ref="chartRef"></div>

<!-- ✅ 正确 -->
<div v-show="!loading" ref="chartRef"></div>
```

### Q2: Element Plus Radio 警告

**原因**: Element Plus 2.6+ 弃用了 `label` 作为值

**解决**:
```vue
<!-- ❌ 旧写法 -->
<el-radio-button label="1M">1个月</el-radio-button>

<!-- ✅ 新写法 -->
<el-radio-button value="1M">1个月</el-radio-button>
```

### Q3: toFixed 报错

**原因**: 后端返回 Decimal 类型是字符串

**解决**:
```typescript
// ❌ 错误
const value = row.cost_nav.toFixed(4)

// ✅ 正确
const value = Number(row.cost_nav || 0).toFixed(4)
```

### Q4: API 数据获取异常

**原因**: `request.ts` 已自动解包 `data.data`，再次访问会出错

**解决**:
```typescript
// ❌ 错误（双重解包）
const response = await fundApi.getHistory(code)
const data = response.data

// ✅ 正确（直接使用）
const data = await fundApi.getHistory(code)
```

### Q5: Store 方法不存在

**原因**: 方法名拼写错误或使用了错误的 Store

**解决**:
```typescript
// 确认 Store 中定义的方法名
const portfolioStore = usePortfolioStore()

// ❌ 错误
portfolioStore.refreshData()

// ✅ 正确
portfolioStore.refreshPortfolio()
```

---

## 相关文档

- [项目README](../README.md) - 项目概览
- [操作手册](OPERATION_MANUAL.md) - 部署和操作指南
- [架构文档](ARCHITECTURE.md) - 系统架构说明
- [故障排查手册](TROUBLESHOOTING.md) - 问题解决方案

---

**Made with ❤️ for investors**
