# 基金跟踪器 v2.0

一款现代化的跨端基金跟踪与分析工具，支持微信小程序、H5、Android App和Windows桌面端。

## 技术架构

### 后端 (Backend)
- **框架**: FastAPI (Python 3.11)
- **数据库**: PostgreSQL 15
- **缓存**: Redis 7
- **ORM**: SQLAlchemy 2.0
- **数据验证**: Pydantic v2

### 前端 (Frontend)
- **框架**: UniApp + Vue 3
- **状态管理**: Pinia
- **UI组件**: uni-ui / uView
- **图表**: uCharts

### AI服务 (AI-Service)
- **OCR**: EasyOCR
- **框架**: FastAPI

## 项目结构

```
fund-tracker/
├── backend/              # FastAPI后端
│   ├── app/
│   │   ├── api/         # API路由
│   │   ├── models/      # 数据库模型
│   │   ├── schemas/     # Pydantic模型
│   │   ├── services/    # 业务逻辑
│   │   └── core/        # 核心配置
│   ├── alembic/         # 数据库迁移
│   └── requirements.txt
├── frontend/            # UniApp前端
│   ├── src/
│   │   ├── pages/       # 页面
│   │   ├── components/  # 组件
│   │   ├── stores/      # Pinia状态
│   │   └── api/         # API封装
│   ├── manifest.json
│   └── pages.json
├── docker/              # Docker配置
└── docs/                # 文档
```

## 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd fund-tracker
```

### 2. 启动后端服务

```bash
# 使用Docker（推荐）
cd docker
docker-compose up -d

# 或使用本地Python环境
cd backend
pip install -r requirements.txt
python -m app.main
```

### 3. 启动前端开发

```bash
cd frontend
npm install
npm run dev:h5      # H5版本
npm run dev:mp-weixin  # 微信小程序
```

## 核心功能

### 已实现功能
- ✅ 基金实时估值查询（多数据源降级）
- ✅ 历史净值数据与图表
- ✅ 持仓管理与盈亏计算
- ✅ 趋势筛选（连续上涨/下跌）
- ✅ 基金搜索
- ✅ 跨端适配

### 待开发功能
- 📸 OCR截图识别基金
- 🤖 AI智能分析建议
- 📊 高级图表对比
- 🔔 实时推送通知
- 👤 用户系统与微信登录

## API文档

启动后端后访问: http://localhost:8000/docs

### 主要接口

```
GET  /api/v1/funds/realtime/{code}      # 实时估值
POST /api/v1/funds/realtime/batch       # 批量实时估值
GET  /api/v1/funds/{code}/history       # 历史数据
POST /api/v1/funds/search               # 搜索基金
GET  /api/v1/portfolio                  # 持仓列表
POST /api/v1/portfolio                  # 添加持仓
POST /api/v1/ocr/extract                # OCR识别基金
```

## 配置说明

### 后端配置 (.env)

```env
DEBUG=true
DATABASE_URL=postgresql://user:pass@localhost:5432/fundtracker
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key
```

### 前端配置

修改 `src/api/request.js` 中的 `BASE_URL`:

```javascript
const BASE_URL = 'http://localhost:8000/api/v1'
```

## 部署指南

### Docker部署

```bash
cd docker
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 微信小程序部署

1. 在 `manifest.json` 中配置小程序 AppID
2. 使用 HBuilderX 或 CLI 构建
3. 上传至微信公众平台

## 开发计划

- Phase 1: 基础架构 ✅
- Phase 2: 核心功能 ✅
- Phase 3: 持仓管理 ✅
- Phase 4: OCR与AI功能 🚧
- Phase 5: 多端适配 🚧

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 许可证

MIT License
