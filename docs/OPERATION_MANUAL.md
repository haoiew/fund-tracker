# 基金跟踪器 - 项目运行操作手册

> 版本: v2.0.0  
> 更新日期: 2026-02-06

---

## 目录

1. [项目概述](#项目概述)
2. [环境要求](#环境要求)
3. [项目结构](#项目结构)
4. [快速开始](#快速开始)
5. [详细部署指南](#详细部署指南)
6. [常用操作命令](#常用操作命令)
7. [故障排查](#故障排查)
8. [前端专项问题](#前端专项问题)
9. [配置文件说明](#配置文件说明)
10. [API接口文档](#api接口文档)
11. [技术栈](#技术栈)

---

## 项目概述

基金跟踪器是一款专为投资者设计的智能基金分析工具，支持多平台使用，提供实时估值、历史数据分析、持仓管理、OCR识别等强大功能。

### 核心特性

- 🚀 **跨端支持**: Web端、桌面端(Windows/Mac/Linux)
- 📊 **实时数据**: 多数据源降级策略，确保数据准确性
- 💰 **持仓管理**: 记录投资金额，实时计算盈亏
- 📸 **OCR识别**: 截图自动识别基金持仓信息
- 🤖 **智能缓存**: Redis缓存加速数据读取
- 📈 **可视化图表**: 丰富的图表展示历史走势
- 🔄 **数据去重**: 自动处理重复持仓数据
- 🎨 **响应式UI**: 基于 Element Plus 的现代化界面

---

## 环境要求

### 必需环境

| 组件 | 版本要求 | 用途 |
|------|----------|------|
| Python | 3.11+ | 后端服务运行环境 |
| Node.js | 18+ | 前端构建和运行 |
| PostgreSQL | 15+ | 主数据库 |
| Redis | 7+ | 缓存服务 |
| Docker | 最新版 | 可选，用于容器化部署 |

### 推荐开发工具

- **IDE**: VS Code + Python插件 + Vue插件 + Volar
- **数据库工具**: DBeaver 或 pgAdmin
- **Redis客户端**: RedisInsight 或 Another Redis Desktop Manager
- **API测试**: Postman 或浏览器访问 Swagger UI
- **Node版本管理**: nvm-windows (Windows) 或 nvm (Mac/Linux)

---

## 项目结构

```
Explore/
├── fund-tracker/                 # Web后端服务
│   ├── backend/                  # FastAPI后端
│   │   ├── app/                  # 应用代码
│   │   │   ├── api/              # API路由
│   │   │   ├── services/         # 业务逻辑
│   │   │   ├── models/           # 数据模型
│   │   │   ├── schemas/          # Pydantic模型
│   │   │   └── config.py         # 配置文件
│   │   ├── requirements.txt      # Python依赖
│   │   └── .env                  # 环境变量
│   └── docs/                     # 项目文档
│
├── fund-tracker-desktop/         # 桌面端前端（主要维护版本）
│   ├── src/                      # 源代码
│   │   ├── views/                # 页面组件
│   │   ├── components/           # 公共组件
│   │   ├── api/                  # API接口
│   │   ├── stores/               # Pinia状态管理
│   │   ├── types/                # TypeScript类型定义
│   │   ├── utils/                # 工具函数
│   │   └── locales/              # 国际化文件
│   ├── package.json              # Node依赖
│   ├── vite.config.ts            # Vite配置
│   └── .env.development          # 开发环境配置
│
├── shared/                       # 共享配置模块
│   └── config.py                 # 统一配置管理
│
├── docker/                       # Docker配置
│   └── docker-compose.yml        # 服务编排
│
├── scripts/                      # 启动脚本
│   ├── start-all.bat             # Windows一键启动
│   ├── stop-all.bat              # Windows一键停止
│   └── restart-all.bat           # Windows一键重启
│
└── docs/                         # 文档目录
    ├── OPERATION_MANUAL.md       # 本手册
    ├── ARCHITECTURE.md           # 架构文档
    ├── FRONTEND_GUIDE.md         # 前端开发指南
    └── TROUBLESHOOTING.md        # 故障排查手册
```

---

## 快速开始

### 方式一：使用一键启动脚本（Windows推荐）

```bash
# 双击运行或命令行执行
scripts\start-all.bat
```

脚本会自动完成以下操作：
1. 检查 Docker 环境
2. 启动 Redis 容器（如未运行）
3. 启动 PostgreSQL 容器（如未运行）
4. 启动后端服务（Python）
5. 启动前端服务（Node.js）
6. 显示访问地址

### 方式二：使用Docker（推荐）

```bash
# 1. 进入docker目录
cd docker

# 2. 启动所有服务（PostgreSQL + Redis + 后端）
docker-compose up -d

# 3. 启动前端（在另一个终端）
cd ../fund-tracker-desktop
npm install
npm run dev
```

### 方式三：手动启动

#### 步骤1：启动基础设施

**Windows PowerShell:**
```powershell
# 启动Redis（使用Docker）
docker run -d --name redis -p 6379:6379 redis:alpine

# 启动PostgreSQL（使用Docker）
docker run -d --name postgres `
  -e POSTGRES_USER=fundtracker `
  -e POSTGRES_PASSWORD=your_password `
  -e POSTGRES_DB=fundtracker `
  -p 5432:5432 postgres:15
```

**Linux/Mac:**
```bash
# 启动Redis
docker run -d --name redis -p 6379:6379 redis:alpine

# 启动PostgreSQL
docker run -d --name postgres \
  -e POSTGRES_USER=fundtracker \
  -e POSTGRES_PASSWORD=your_password \
  -e POSTGRES_DB=fundtracker \
  -p 5432:5432 postgres:15
```

#### 步骤2：启动后端服务

```bash
# 进入后端目录
cd fund-tracker/backend

# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
copy .env.example .env
# 编辑 .env 文件，修改数据库连接信息

# 启动服务
python -m app.main
```

后端服务启动成功后，访问:
- API文档: http://localhost:8001/docs
- 健康检查: http://localhost:8001/health

#### 步骤3：启动前端服务

```bash
# 进入前端目录
cd fund-tracker-desktop

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端启动成功后，访问: http://localhost:5173

---

## 详细部署指南

### 后端服务部署

#### 1. 环境配置

创建 `.env` 文件：

```env
# 数据库配置
DATABASE_URL=postgresql://fundtracker:your_password@localhost:5432/fundtracker

# Redis配置
REDIS_URL=redis://localhost:6379/0

# 安全密钥
SECRET_KEY=your-secret-key-here

# 应用配置
APP_NAME=基金跟踪器
APP_VERSION=2.0.0
DEBUG=true

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

#### 2. 数据库初始化

```bash
# 进入后端目录
cd fund-tracker/backend

# 激活虚拟环境
venv\Scripts\activate

# 运行数据库迁移（自动创建表）
python -c "from app.db.base import Base, engine; Base.metadata.create_all(bind=engine)"
```

#### 3. 服务启动参数

```bash
# 开发模式（热重载）
python -m app.main

# 生产模式（使用uvicorn）
uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 4
```

### 前端服务部署

#### 1. 环境配置

创建 `.env.local` 文件：

```env
# API地址
VITE_API_BASE_URL=http://localhost:8001/api/v1

# 其他配置
VITE_APP_TITLE=基金跟踪器
VITE_APP_VERSION=2.0.0
```

#### 2. 开发模式

```bash
npm run dev
```

#### 3. 生产构建

```bash
# 构建生产版本
npm run build

# 预览生产构建
npm run preview

# 构建Electron应用
npm run electron:build
```

---

## 常用操作命令

### 一键脚本（Windows）

项目提供了便捷的批处理脚本，位于 `scripts/` 目录：

| 脚本 | 功能 | 使用方式 |
|------|------|----------|
| `start-all.bat` | 一键启动所有服务 | 双击运行或命令行执行 |
| `stop-all.bat` | 一键停止所有服务 | 双击运行或命令行执行 |
| `restart-all.bat` | 一键重启所有服务 | 双击运行或命令行执行 |
| `status.bat` | 查看服务运行状态 | 双击运行或命令行执行 |

**使用示例：**

```bash
# 启动所有服务
scripts\start-all.bat

# 查看服务状态
scripts\status.bat

# 停止所有服务（会询问是否停止数据库）
scripts\stop-all.bat

# 重启所有服务
scripts\restart-all.bat
```

### 服务管理

```bash
# 查看运行中的容器
docker ps

# 查看Redis状态
docker exec -it redis redis-cli ping

# 查看PostgreSQL状态
docker exec -it postgres pg_isready

# 重启后端服务
# 按 Ctrl+C 停止，然后重新运行
python -m app.main

# 重启前端服务
# 按 Ctrl+C 停止，然后重新运行
npm run dev
```

### 数据库操作

```bash
# 进入PostgreSQL容器
docker exec -it postgres psql -U fundtracker -d fundtracker

# 常用SQL命令
\dt                    # 查看所有表
\q                     # 退出
SELECT * FROM funds;   # 查看基金表
SELECT * FROM portfolio;  # 查看持仓表
```

### Redis操作

```bash
# 进入Redis容器
docker exec -it redis redis-cli

# 常用命令
KEYS *                 # 查看所有键
GET realtime:000001    # 查看特定基金缓存
FLUSHALL               # 清空所有缓存（谨慎使用）
INFO stats             # 查看统计信息
```

### 日志查看

```bash
# 后端日志（实时）
tail -f fund-tracker/backend/logs/app.log

# Docker日志
docker logs -f <container_id>

# 前端日志（浏览器控制台）
# 按 F12 打开开发者工具查看
```

---

## 故障排查

### 问题1：后端启动失败

**现象**: `python -m app.main` 报错

**排查步骤**:
1. 检查虚拟环境是否激活
2. 检查依赖是否安装完整: `pip list | grep -E "fastapi|sqlalchemy"`
3. 检查数据库连接: 确认PostgreSQL已启动且连接信息正确
4. 检查Redis连接: 确认Redis已启动
5. 查看详细错误日志

**解决方案**:
```bash
# 重新安装依赖
pip install -r requirements.txt --force-reinstall

# 检查端口占用
netstat -ano | findstr 8001
```

### 问题2：前端无法连接后端

**现象**: 页面显示"网络错误"或"连接失败"

**排查步骤**:
1. 检查后端是否正常运行: `curl http://localhost:8001/health`
2. 检查前端API配置: 查看 `.env.local` 中的 `VITE_API_BASE_URL`
3. 检查浏览器控制台网络请求
4. 检查CORS配置: 确认后端 `.env` 中的 `CORS_ORIGINS` 包含前端地址

**解决方案**:
```bash
# 检查后端健康状态
curl http://localhost:8001/health

# 修改前端配置后重启
npm run dev
```

### 问题3：Redis连接失败

**现象**: 日志显示 "Redis连接失败"

**排查步骤**:
1. 检查Redis容器状态: `docker ps | findstr redis`
2. 检查Redis端口: `netstat -ano | findstr 6379`
3. 检查防火墙设置

**解决方案**:
```bash
# 重启Redis
docker restart redis

# 或者重新创建
docker rm -f redis
docker run -d --name redis -p 6379:6379 redis:alpine
```

### 问题4：数据库连接失败

**现象**: 日志显示 "数据库连接失败"

**排查步骤**:
1. 检查PostgreSQL容器状态
2. 检查数据库连接字符串
3. 检查数据库用户权限

**解决方案**:
```bash
# 检查PostgreSQL日志
docker logs postgres

# 重新创建数据库
docker rm -f postgres
docker run -d --name postgres `
  -e POSTGRES_USER=fundtracker `
  -e POSTGRES_PASSWORD=your_password `
  -e POSTGRES_DB=fundtracker `
  -p 5432:5432 postgres:15
```

### 问题5：OCR识别失败

**现象**: 上传截图后提示"识别失败"

**排查步骤**:
1. 检查EasyOCR是否初始化成功（查看启动日志）
2. 检查图片格式是否支持（JPG、PNG）
3. 检查后端日志中的OCR识别过程

**解决方案**:
```bash
# 重新安装OCR依赖
pip install easyocr pillow numpy

# 检查OCR模型文件是否下载完整
```

### 问题6：缓存不生效

**现象**: 数据加载慢，缓存命中率低

**排查步骤**:
1. 检查Redis是否启用: 查看启动日志
2. 检查缓存统计: 访问 `http://localhost:8001/api/v1/funds/cache/stats`
3. 检查缓存键是否正确生成

**解决方案**:
```bash
# 清空缓存后重启
docker exec -it redis redis-cli FLUSHALL

# 重启后端服务
```

---

## 前端专项问题

### 问题1：图表容器未准备好

**现象**: 控制台报错 "图表容器未准备好"

**原因**: 使用 `v-if` 控制图表容器显示，导致 ECharts 初始化时容器不存在

**解决方案**:
```vue
<!-- ❌ 错误 -->
<div v-if="!loading" ref="chartRef"></div>

<!-- ✅ 正确 -->
<div v-show="!loading" ref="chartRef"></div>
```

### 问题2：Element Plus Radio 警告

**现象**: 控制台警告 "label act as value is about to be deprecated"

**原因**: Element Plus 2.6+ 版本弃用了 `label` 作为值的做法

**解决方案**:
```vue
<!-- ❌ 旧写法 -->
<el-radio-button label="1M">1个月</el-radio-button>

<!-- ✅ 新写法 -->
<el-radio-button value="1M">1个月</el-radio-button>
```

### 问题3：toFixed 报错

**现象**: 报错 "toFixed is not a function"

**原因**: 后端返回的 Decimal 类型是字符串，不是 Number

**解决方案**:
```typescript
// ❌ 错误
const value = row.cost_nav.toFixed(4)

// ✅ 正确
const value = Number(row.cost_nav || 0).toFixed(4)
```

### 问题4：API 数据双重解包

**现象**: 获取不到数据，或数据结构异常

**原因**: `request.ts` 的响应拦截器已经解包了 `data.data`，再次访问 `.data` 会导致问题

**解决方案**:
```typescript
// ❌ 错误（双重解包）
const response = await fundApi.getHistory(code)
const data = response.data.data

// ✅ 正确（直接使用）
const data = await fundApi.getHistory(code)
```

### 问题5：持仓数据重复

**现象**: 持仓列表显示重复基金

**原因**: 后端或本地存储可能返回重复数据

**解决方案**: 已在 `dataManager.ts` 中实现自动去重
```typescript
// 去重逻辑：根据 id 去重，保留最新的数据
const uniqueMap = new Map<number, PortfolioItem>()
newItems.forEach(item => {
  if (item.id !== undefined) {
    uniqueMap.set(item.id, item)
  }
})
newItems = Array.from(uniqueMap.values())
```

### 问题6：Pinia Store 方法不存在

**现象**: 报错 "refreshData is not a function"

**原因**: Store 中导出的方法名与实际调用不一致

**解决方案**:
```typescript
// store 中定义
export const usePortfolioStore = defineStore('portfolio', {
  actions: {
    async refreshPortfolio() {
      // ...
    }
  }
})

// 组件中调用
const portfolioStore = usePortfolioStore()

// ❌ 错误
portfolioStore.refreshData()

// ✅ 正确
portfolioStore.refreshPortfolio()
```

---

## 配置文件说明

### 后端配置 (fund-tracker/backend/.env)

| 配置项 | 说明 | 示例 |
|--------|------|------|
| DATABASE_URL | PostgreSQL连接字符串 | `postgresql://user:pass@localhost:5432/dbname` |
| REDIS_URL | Redis连接字符串 | `redis://localhost:6379/0` |
| SECRET_KEY | JWT加密密钥 | 随机字符串 |
| DEBUG | 调试模式 | `true` 或 `false` |
| LOG_LEVEL | 日志级别 | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| CORS_ORIGINS | 允许的跨域来源 | `http://localhost:5173,http://localhost:8000` |

### 前端配置 (fund-tracker-desktop/.env.local)

| 配置项 | 说明 | 示例 |
|--------|------|------|
| VITE_API_BASE_URL | 后端API地址 | `http://localhost:8001/api/v1` |
| VITE_APP_TITLE | 应用标题 | `基金跟踪器` |
| VITE_APP_VERSION | 应用版本 | `2.0.0` |

### 共享配置 (shared/config.py)

| 配置类 | 用途 |
|--------|------|
| FundConfig | 基金代码列表、默认基金、筛选条件 |
| ChartConfig | 图表时间范围、样式配置 |
| ServerConfig | 服务器端口、CORS配置 |
| OcrConfig | OCR模型路径、置信度阈值 |

---

## API接口文档

### 在线文档

启动后端服务后访问:
- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

### 常用接口

#### 基金相关

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/funds/realtime/{code}` | 获取基金实时估值 |
| POST | `/api/v1/funds/realtime/batch` | 批量获取实时估值 |
| GET | `/api/v1/funds/{code}/history` | 获取历史净值数据 |
| POST | `/api/v1/funds/search` | 搜索基金 |
| GET | `/api/v1/funds/cache/stats` | 获取缓存统计 |

#### 持仓相关

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/portfolio` | 获取持仓列表 |
| POST | `/api/v1/portfolio` | 添加持仓 |
| PUT | `/api/v1/portfolio/{id}` | 更新持仓 |
| DELETE | `/api/v1/portfolio/{id}` | 删除持仓 |
| GET | `/api/v1/portfolio/summary` | 获取持仓汇总 |

#### OCR相关

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/ocr/scan` | OCR扫描图片 |
| POST | `/api/v1/ocr/extract` | 提取持仓信息 |

### 响应格式

所有API响应遵循统一格式：

```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```

**注意**: 前端 `request.ts` 会自动解包 `data` 字段，组件中直接获取数据即可。

---

## 技术栈

### 后端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.11+ | 编程语言 |
| FastAPI | 0.104+ | Web框架 |
| SQLAlchemy | 2.0+ | ORM框架 |
| PostgreSQL | 15+ | 关系数据库 |
| Redis | 7+ | 缓存数据库 |
| EasyOCR | 1.7+ | OCR识别 |
| APScheduler | 3.10+ | 定时任务 |
| Pydantic | 2.5+ | 数据验证 |

### 前端技术栈

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

---

## 性能优化建议

### 后端优化

1. **启用Redis缓存**: 确保 `REDIS_URL` 配置正确
2. **调整缓存TTL**: 根据数据更新频率调整缓存时间
3. **数据库连接池**: 调整 `SQLALCHEMY_POOL_SIZE`
4. **使用Gunicorn**: 生产环境使用 `gunicorn` + `uvicorn.workers.UvicornWorker`

### 前端优化

1. **启用CDN**: 生产环境使用CDN加速静态资源
2. **代码分割**: 使用Vite的代码分割功能
3. **图片优化**: 压缩图片，使用WebP格式
4. **懒加载**: 路由和组件懒加载
5. **LocalStorage缓存**: 合理使用本地缓存减少API请求

---

## 安全注意事项

1. **修改默认密钥**: 生产环境必须修改 `SECRET_KEY`
2. **数据库密码**: 使用强密码，定期更换
3. **HTTPS**: 生产环境启用HTTPS
4. **CORS配置**: 限制允许的域名
5. **输入验证**: 所有用户输入都需要验证
6. **环境变量**: 不要将 `.env` 文件提交到版本控制

---

## 更新日志

### v2.0.0 (2026-02-06)

- ✨ 新增桌面端支持
- ✨ 新增OCR持仓识别
- ✨ 新增Redis缓存
- ✨ 新增数据去重机制
- ✨ 新增多语言支持
- 🐛 修复图表渲染问题
- 🐛 修复数据类型转换问题
- 🐛 修复缓存序列化问题
- 🐛 修复Element Plus警告
- ♻️ 重构Portfolio服务
- ♻️ 重构数据管理器
- 📚 完善文档

---

## 相关文档

- [项目README](../README.md) - 项目概览和快速开始
- [架构文档](ARCHITECTURE.md) - 系统架构详细说明
- [前端开发指南](FRONTEND_GUIDE.md) - 前端开发规范
- [故障排查手册](TROUBLESHOOTING.md) - 详细问题解决方案

---

## 支持与反馈

如有问题，请通过以下方式联系：

- 提交Issue: [GitHub Issues]
- 邮件支持: support@example.com

---

**Made with ❤️ for investors**
