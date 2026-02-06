# 基金跟踪器 - 故障排查手册

> 版本: v2.0.0  
> 更新日期: 2026-02-06

---

## 目录

1. [前端问题](#前端问题)
2. [后端问题](#后端问题)
3. [数据问题](#数据问题)
4. [环境问题](#环境问题)
5. [性能问题](#性能问题)
6. [调试技巧](#调试技巧)

---

## 前端问题

### 1. 图表不显示或报错 "图表容器未准备好"

**现象**: 控制台报错 `Error: 图表容器未准备好` 或图表区域空白

**原因**: 使用 `v-if` 控制图表容器显示，导致 ECharts 初始化时 DOM 元素不存在

**解决方案**:
```vue
<!-- ❌ 错误写法 -->
<div v-if="!loading" ref="chartRef" class="chart-container"></div>
<div v-else class="loading">加载中...</div>

<!-- ✅ 正确写法 -->
<div v-show="loading" class="chart-loading">
  <el-skeleton :rows="5" animated />
</div>
<div v-show="!loading" ref="chartRef" class="chart-container"></div>
```

**说明**: `v-show` 只是切换 CSS `display` 属性，元素始终存在于 DOM 中；`v-if` 会真正移除/创建元素。

---

### 2. Element Plus Radio 警告

**现象**: 控制台警告 `label act as value is about to be deprecated`

**原因**: Element Plus 2.6+ 版本弃用了 `label` 属性作为值的做法，改用 `value` 属性

**解决方案**:
```vue
<!-- ❌ 旧写法（已弃用） -->
<el-radio-group v-model="timeRange">
  <el-radio-button label="1M">1个月</el-radio-button>
  <el-radio-button label="3M">3个月</el-radio-button>
  <el-radio-button label="6M">6个月</el-radio-button>
</el-radio-group>

<!-- ✅ 新写法 -->
<el-radio-group v-model="timeRange">
  <el-radio-button value="1M">1个月</el-radio-button>
  <el-radio-button value="3M">3个月</el-radio-button>
  <el-radio-button value="6M">6个月</el-radio-button>
</el-radio-group>
```

**影响文件**: 
- `FundDetailDialog.vue`
- `FundChart.vue`
- `ScreenView.vue`
- `CompareView.vue`
- `HomeView.vue`
- `SettingsView.vue`

---

### 3. toFixed 报错 "is not a function"

**现象**: 报错 `row.cost_nav.toFixed is not a function` 或类似错误

**原因**: 后端返回的 Decimal 类型字段是字符串格式，不是 Number 类型

**解决方案**:
```typescript
// ❌ 错误（cost_nav 可能是字符串）
const costNav = row.cost_nav.toFixed(4)

// ✅ 正确（先转换为 Number）
const costNav = Number(row.cost_nav || 0).toFixed(4)

// ✅ 更安全的写法（处理 null/undefined/空字符串）
const formatNumber = (value: number | string | null | undefined, digits = 4): string => {
  const num = Number(value)
  return isNaN(num) ? '0.0000' : num.toFixed(digits)
}

// 使用
const costNav = formatNumber(row.cost_nav)
const marketValue = formatNumber(row.market_value, 2)
```

**常见需要处理的字段**:
- `cost_nav` - 成本净值
- `shares` - 持有份额
- `market_value` - 市值
- `profit` - 盈亏金额

---

### 4. API 数据双重解包

**现象**: 获取不到数据，或数据结构异常，或报错 `Cannot read property 'xxx' of undefined`

**原因**: `request.ts` 中的响应拦截器已经自动解包了 `response.data.data`，如果再次访问 `.data` 会导致双重解包

**request.ts 拦截器逻辑**:
```typescript
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

**解决方案**:
```typescript
// ❌ 错误（双重解包，data 是 undefined）
const response = await fundApi.getHistory(code, range)
const data = response.data  // response 已经是 data.data 了
console.log(data.dates)     // 报错！

// ✅ 正确（直接使用）
const data = await fundApi.getHistory(code, range)
console.log(data.dates)     // 正常工作

// ✅ 如果需要完整响应（极少数情况）
const response = await axios.get('/api/v1/funds/history')
const apiResponse = response.data  // { code, message, data }
const data = apiResponse.data
```

**API 响应格式**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "dates": ["2024-01-01", "2024-01-02"],
    "navs": [1.2345, 1.2356]
  }
}
```

---

### 5. Pinia Store 方法不存在

**现象**: 报错 `portfolioStore.refreshData is not a function`

**原因**: Store 中定义的方法名与实际调用的方法名不一致

**解决方案**:
```typescript
// stores/portfolioStore.ts
export const usePortfolioStore = defineStore('portfolio', {
  actions: {
    // 定义的方法名
    async refreshPortfolio() {
      // ...
    },
    
    async addPosition(item: PortfolioItem) {
      // ...
    }
  }
})

// 组件中使用
const portfolioStore = usePortfolioStore()

// ❌ 错误（方法名不匹配）
portfolioStore.refreshData()

// ✅ 正确
portfolioStore.refreshPortfolio()
```

**常见方法名对照**:
| 错误调用 | 正确调用 |
|---------|---------|
| `refreshData()` | `refreshPortfolio()` |
| `addItem()` | `addPosition()` |
| `removeItem()` | `removePosition()` |
| `updateItem()` | `updatePosition()` |

---

### 6. 持仓数据重复

**现象**: 持仓列表中显示重复的基金条目

**原因**: 
1. 后端返回了重复数据
2. 本地存储和 API 数据合并时产生重复
3. 并发请求导致数据竞争

**解决方案**: 已在 `dataManager.ts` 中实现自动去重

```typescript
// stores/dataManager.ts

async loadPortfolioFromStorage(): Promise<PortfolioItem[]> {
  let newItems: PortfolioItem[] = []
  
  // 从本地存储加载
  const stored = localStorage.getItem('portfolio')
  if (stored) {
    try {
      const parsed = JSON.parse(stored)
      newItems = parsed.data || []
    } catch (e) {
      console.error('解析本地持仓数据失败:', e)
    }
  }
  
  // 从 API 获取最新数据
  try {
    const response = await portfolioApi.getList()
    if (Array.isArray(response)) {
      newItems = response
    }
  } catch (error) {
    console.warn('从API获取持仓失败，使用本地数据:', error)
  }
  
  // 去重：根据 id 去重，保留最新的数据
  const uniqueMap = new Map<number, PortfolioItem>()
  newItems.forEach(item => {
    if (item.id !== undefined) {
      uniqueMap.set(item.id, item)
    } else {
      // 对于没有 id 的数据，使用 fund_code 去重
      const existing = Array.from(uniqueMap.values()).find(
        i => i.fund_code === item.fund_code
      )
      if (!existing) {
        uniqueMap.set(Date.now() + Math.random(), item)
      }
    }
  })
  
  newItems = Array.from(uniqueMap.values())
  
  // 更新本地存储
  localStorage.setItem('portfolio', JSON.stringify({
    data: newItems,
    timestamp: Date.now()
  }))
  
  return newItems
}
```

---

### 7. 响应式数据不更新

**现象**: 修改了数据但 UI 没有更新

**原因**: 
1. 直接修改了数组/对象的属性
2. 使用了非响应式的方式创建数据

**解决方案**:
```typescript
// ❌ 错误（直接修改数组元素）
const fundList = ref<Fund[]>([])
fundList.value[0].nav = 1.5  // 不会触发更新

// ✅ 正确（使用 splice 或重新赋值）
fundList.value[0] = { ...fundList.value[0], nav: 1.5 }
// 或者
fundList.value = fundList.value.map((fund, index) => 
  index === 0 ? { ...fund, nav: 1.5 } : fund
)

// ❌ 错误（直接添加新属性）
const fund = reactive({ name: '基金A', code: '000001' })
fund.nav = 1.5  // 不会触发更新

// ✅ 正确（使用 Object.assign 或提前声明）
const fund = reactive({ name: '基金A', code: '000001', nav: null })
fund.nav = 1.5  // 正常更新
```

---

## 后端问题

### 1. 后端启动失败

**现象**: 运行 `python -m app.main` 报错

**排查步骤**:

```bash
# 1. 检查虚拟环境是否激活
which python  # 应该指向 venv 中的 python

# 2. 检查依赖是否安装完整
pip list | grep -E "fastapi|sqlalchemy|uvicorn"

# 3. 检查数据库连接
# 查看 .env 中的 DATABASE_URL 是否正确
cat fund-tracker/backend/.env | grep DATABASE_URL

# 4. 检查端口占用
netstat -ano | findstr 8001  # Windows
lsof -i :8001                # Mac/Linux

# 5. 查看详细错误日志
python -m app.main 2>&1 | tee error.log
```

**常见错误及解决方案**:

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `ModuleNotFoundError` | 依赖未安装 | `pip install -r requirements.txt` |
| `Connection refused` | 数据库未启动 | 启动 PostgreSQL 容器 |
| `Address already in use` | 端口被占用 | 更换端口或停止占用进程 |
| `ImportError` | Python 路径问题 | 检查虚拟环境激活状态 |

---

### 2. 数据库连接失败

**现象**: 日志显示 `数据库连接失败` 或 `could not connect to server`

**排查步骤**:

```bash
# 1. 检查 PostgreSQL 容器状态
docker ps | grep postgres

# 2. 检查数据库连接信息
cat fund-tracker/backend/.env
# 应该包含：
# DATABASE_URL=postgresql://fundtracker:your_password@localhost:5432/fundtracker

# 3. 测试数据库连接
docker exec -it postgres psql -U fundtracker -d fundtracker -c "SELECT 1"

# 4. 检查数据库是否存在
docker exec -it postgres psql -U fundtracker -l

# 5. 查看 PostgreSQL 日志
docker logs postgres
```

**解决方案**:

```bash
# 重新创建数据库容器
docker rm -f postgres
docker run -d --name postgres \
  -e POSTGRES_USER=fundtracker \
  -e POSTGRES_PASSWORD=your_password \
  -e POSTGRES_DB=fundtracker \
  -p 5432:5432 \
  postgres:15

# 等待数据库启动
docker exec -it postgres pg_isready

# 重新初始化表结构
cd fund-tracker/backend
python -c "from app.db.base import Base, engine; Base.metadata.create_all(bind=engine)"
```

---

### 3. Redis 连接失败

**现象**: 日志显示 `Redis连接失败` 或 `Error connecting to Redis`

**排查步骤**:

```bash
# 1. 检查 Redis 容器状态
docker ps | grep redis

# 2. 测试 Redis 连接
docker exec -it redis redis-cli ping
# 应该返回 PONG

# 3. 检查 Redis 配置
cat fund-tracker/backend/.env | grep REDIS_URL
# 应该包含：
# REDIS_URL=redis://localhost:6379/0

# 4. 检查端口占用
netstat -ano | findstr 6379
```

**解决方案**:

```bash
# 重启 Redis
docker restart redis

# 或重新创建
docker rm -f redis
docker run -d --name redis -p 6379:6379 redis:alpine

# 清空 Redis 缓存（谨慎使用）
docker exec -it redis redis-cli FLUSHALL
```

---

### 4. CORS 跨域错误

**现象**: 浏览器控制台报错 `Access-Control-Allow-Origin` 或 `CORS policy`

**原因**: 后端未配置允许的前端域名

**解决方案**:

```bash
# 编辑后端 .env 文件
cat fund-tracker/backend/.env

# 确保包含前端地址
CORS_ORIGINS=http://localhost:5173,http://localhost:8000

# 重启后端服务
```

**后端 CORS 配置**:

```python
# fund-tracker/backend/app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 数据问题

### 1. 基金数据不更新

**现象**: 基金净值数据长时间不更新

**排查步骤**:

```bash
# 1. 检查缓存状态
curl http://localhost:8001/api/v1/funds/cache/stats

# 2. 检查数据源可用性
# 查看后端日志，检查是否有数据源请求失败

# 3. 手动刷新缓存
curl -X POST http://localhost:8001/api/v1/funds/cache/clear

# 4. 检查 Redis 缓存
docker exec -it redis redis-cli KEYS "realtime:*"
```

**解决方案**:

```bash
# 清空 Redis 缓存
docker exec -it redis redis-cli FLUSHALL

# 重启后端服务
# 重新获取数据
```

---

### 2. 历史净值数据缺失

**现象**: 基金走势图数据点不足或为空

**原因**: 
1. 新添加的基金没有历史数据
2. 数据源返回的数据不完整
3. 数据库中没有该基金的历史记录

**解决方案**:

```python
# 手动同步历史数据（后端）
from app.services.fund_service import FundService

service = FundService()
await service.sync_fund_history("000001", days=365)
```

---

### 3. OCR 识别失败

**现象**: 上传截图后提示"识别失败"或返回空结果

**排查步骤**:

```bash
# 1. 检查 EasyOCR 是否初始化成功
# 查看后端启动日志，搜索 "OCR"

# 2. 检查图片格式
# 支持的格式：JPG, PNG
# 最大尺寸：建议不超过 5MB

# 3. 检查图片内容
# 确保图片包含基金代码和持仓信息
# 确保文字清晰可辨认
```

**解决方案**:

```bash
# 重新安装 OCR 依赖
pip install easyocr pillow numpy --force-reinstall

# 检查模型文件
# 模型文件通常位于 ~/.EasyOCR/
ls -la ~/.EasyOCR/

# 手动下载模型（如果需要）
# 参考 EasyOCR 官方文档
```

---

## 环境问题

### 1. Node.js 版本不兼容

**现象**: 安装依赖时报错 `engines.node` 或运行时报错

**解决方案**:

```bash
# 检查 Node.js 版本
node -v  # 需要 v18+

# 使用 nvm 切换版本
nvm install 18
nvm use 18

# 或使用 n
npm install -g n
n 18

# 重新安装依赖
rm -rf node_modules package-lock.json
npm install
```

---

### 2. Python 虚拟环境问题

**现象**: `ModuleNotFoundError` 或导入错误

**解决方案**:

```bash
# Windows
# 重新创建虚拟环境
cd fund-tracker/backend
rmdir /s venv
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Mac/Linux
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

### 3. Docker 容器无法启动

**现象**: `docker run` 报错或容器立即退出

**排查步骤**:

```bash
# 1. 检查 Docker 服务状态
docker info

# 2. 查看容器日志
docker logs <container_id>

# 3. 检查端口占用
netstat -ano | findstr 5432
netstat -ano | findstr 6379

# 4. 检查磁盘空间
docker system df
```

**解决方案**:

```bash
# 清理 Docker 资源
docker system prune -a

# 重新创建容器
docker-compose down
docker-compose up -d
```

---

## 性能问题

### 1. 页面加载缓慢

**原因分析**:
1. 首次加载资源过大
2. API 响应慢
3. 数据量过大

**解决方案**:

```typescript
// 1. 启用路由懒加载
// router/index.ts
const routes = [
  {
    path: '/portfolio',
    component: () => import('@/views/Portfolio/PortfolioView.vue')
  }
]

// 2. 使用虚拟列表（大数据量）
// 安装 vue-virtual-scroller
npm install vue-virtual-scroller

// 3. 优化 API 请求
// 使用防抖
import { debounce } from 'lodash-es'

const searchFunds = debounce(async (keyword: string) => {
  const results = await fundApi.search(keyword)
  fundList.value = results
}, 300)
```

---

### 2. 内存泄漏

**现象**: 页面长时间运行后变慢或崩溃

**常见原因**:
1. 事件监听器未移除
2. 定时器未清除
3. ECharts 实例未销毁

**解决方案**:

```typescript
// ❌ 错误（未清理）
onMounted(() => {
  window.addEventListener('resize', handleResize)
  setInterval(fetchData, 5000)
})

// ✅ 正确（清理资源）
onMounted(() => {
  window.addEventListener('resize', handleResize)
  const timer = setInterval(fetchData, 5000)
  
  onUnmounted(() => {
    window.removeEventListener('resize', handleResize)
    clearInterval(timer)
  })
})

// ECharts 实例清理
let chart: echarts.ECharts | null = null

onMounted(() => {
  chart = echarts.init(chartRef.value)
})

onUnmounted(() => {
  chart?.dispose()
  chart = null
})
```

---

### 3. 大数据量渲染卡顿

**解决方案**:

```typescript
// 1. 分页加载
const loadMore = async () => {
  if (loading.value || noMore.value) return
  
  loading.value = true
  const data = await fundApi.getList({
    page: currentPage.value,
    pageSize: 20
  })
  
  fundList.value.push(...data.list)
  noMore.value = data.list.length < 20
  currentPage.value++
  loading.value = false
}

// 2. 虚拟滚动
import { RecycleScroller } from 'vue-virtual-scroller'

<template>
  <RecycleScroller
    class="scroller"
    :items="fundList"
    :item-size="60"
    key-field="code"
  >
    <template #default="{ item }">
      <FundCard :fund="item" />
    </template>
  </RecycleScroller>
</template>
```

---

## 调试技巧

### 1. 浏览器调试

```javascript
// 在控制台查看 Pinia Store 状态
__VUE_DEVTOOLS_GLOBAL_HOOK__.emit('vuex:mutation')

// 查看 LocalStorage
JSON.parse(localStorage.getItem('portfolio'))

// 查看当前路由
__VUE_ROUTER__

// 强制刷新页面（忽略缓存）
location.reload(true)
```

### 2. Vue DevTools

安装 Vue DevTools 浏览器扩展：
- 查看组件树
- 检查组件 props/data/computed
- 查看 Pinia Store 状态
- 时间旅行调试

### 3. 后端调试

```python
# 添加断点
import pdb; pdb.set_trace()

# 或使用 ipdb
import ipdb; ipdb.set_trace()

# 打印调试信息
import logging
logger = logging.getLogger(__name__)
logger.debug(f" fund data: {fund_data}")
```

### 4. 网络调试

```bash
# 使用 curl 测试 API
curl -v http://localhost:8001/api/v1/funds/realtime/000001

# 使用 httpie（更友好）
http :8001/api/v1/funds/realtime/000001

# 查看请求头
http :8001/api/v1/funds/realtime/000001 --print=H
```

### 5. 日志级别调整

```bash
# 后端：调整日志级别
# .env
LOG_LEVEL=DEBUG

# 前端：启用 Vue 详细日志
# main.ts
app.config.warnHandler = (msg, instance, trace) => {
  console.warn('[Vue warn]:', msg, trace)
}
```

---

## 快速诊断清单

遇到问题时，按以下顺序检查：

1. **检查服务状态**
   - [ ] 后端服务是否运行？
   - [ ] 前端服务是否运行？
   - [ ] PostgreSQL 是否运行？
   - [ ] Redis 是否运行？

2. **检查配置**
   - [ ] `.env` 文件配置是否正确？
   - [ ] API 地址是否正确？
   - [ ] CORS 配置是否包含前端地址？

3. **检查网络**
   - [ ] 浏览器控制台是否有网络错误？
   - [ ] 后端日志是否有请求记录？
   - [ ] 防火墙是否阻止了端口？

4. **检查数据**
   - [ ] 数据库是否有数据？
   - [ ] Redis 缓存是否正常？
   - [ ] 本地存储是否损坏？

5. **检查代码**
   - [ ] 是否有语法错误？
   - [ ] 依赖是否正确安装？
   - [ ] 类型定义是否匹配？

---

## 相关文档

- [项目README](../README.md) - 项目概览
- [操作手册](OPERATION_MANUAL.md) - 部署和操作指南
- [架构文档](ARCHITECTURE.md) - 系统架构说明
- [前端开发指南](FRONTEND_GUIDE.md) - 前端开发规范

---

**Made with ❤️ for investors**
