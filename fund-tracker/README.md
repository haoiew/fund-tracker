# 基金跟踪器 Fund Tracker v2.0

> 现代化的跨端基金跟踪与分析工具

## 项目简介

基金跟踪器是一款专为投资者设计的智能基金分析工具，支持多平台使用，提供实时估值、历史数据分析、持仓管理、OCR识别等强大功能。

### 核心特性

- 🚀 **跨端支持**: 微信小程序、H5、Android App、Windows桌面端
- 📊 **实时数据**: 多数据源降级策略，确保数据准确性
- 💰 **持仓管理**: 记录投资金额，实时计算盈亏
- 📸 **OCR识别**: 截图自动识别基金代码和名称
- 🤖 **智能分析**: AI驱动的投资建议
- 📈 **可视化图表**: 丰富的图表展示历史走势

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | UniApp + Vue 3 + Pinia |
| 后端 | FastAPI + SQLAlchemy |
| 数据库 | PostgreSQL + Redis |
| AI | EasyOCR |
| 部署 | Docker |

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- PostgreSQL 15
- Redis 7

### 安装运行

```bash
# 1. 启动基础设施
cd docker
docker-compose up -d postgres redis

# 2. 启动后端
cd ../backend
pip install -r requirements.txt
python -m app.main

# 3. 启动前端
cd ../frontend
npm install
npm run dev:h5
```

访问 http://localhost:8000/docs 查看API文档

## 项目结构

```
fund-tracker/
├── backend/          # FastAPI后端服务
├── frontend/         # UniApp前端应用
├── ai-service/       # AI识别服务
├── docker/           # Docker配置
└── docs/             # 项目文档
```

## 功能模块

### 1. 基金数据模块
- 实时估值查询（天天基金、新浪、AKShare多源）
- 历史净值数据获取
- 涨跌幅趋势分析
- 基金搜索

### 2. 持仓管理模块
- 添加/删除持仓
- 记录购买金额和份额
- 实时盈亏计算
- 资产分布统计

### 3. OCR识别模块
- 截图上传识别
- 基金代码/名称提取
- 自动匹配基金信息

### 4. 可视化模块
- K线/净值走势图
- 涨跌幅柱状图
- 资产分布饼图
- 多基金对比图

## 配置说明

### 后端配置

复制 `.env.example` 为 `.env` 并修改：

```env
DATABASE_URL=postgresql://user:pass@localhost:5432/fundtracker
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key
```

### 前端配置

修改 `frontend/src/api/request.js` 中的API地址：

```javascript
const BASE_URL = 'http://your-api-domain/api/v1'
```

## API接口

### 基金相关
- `GET /api/v1/funds/realtime/{code}` - 获取实时估值
- `POST /api/v1/funds/realtime/batch` - 批量获取实时估值
- `GET /api/v1/funds/{code}/history` - 获取历史数据
- `POST /api/v1/funds/search` - 搜索基金

### 持仓相关
- `GET /api/v1/portfolio` - 获取持仓列表
- `POST /api/v1/portfolio` - 添加持仓
- `GET /api/v1/portfolio/profit` - 获取收益统计

### OCR相关
- `POST /api/v1/ocr/scan` - OCR扫描图片
- `POST /api/v1/ocr/extract` - 提取基金信息

## 部署

### Docker部署

```bash
cd docker
docker-compose up -d
```

### 微信小程序

1. 配置 `manifest.json` 中的 AppID
2. 使用 HBuilderX 构建
3. 上传至微信开发者工具

## 开发计划

- [x] 基础架构搭建
- [x] 基金数据API
- [x] 持仓管理功能
- [x] 前端基础页面
- [ ] OCR识别功能
- [ ] AI智能分析
- [ ] 微信小程序适配
- [ ] Android App打包

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可

MIT License

---

Made with ❤️ for investors
