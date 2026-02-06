# 统一配置模块使用说明

## 概述

`shared/config.py` 提供了跨项目的统一配置管理，支持 fund_core.py、fund-tracker、fund-tracker-desktop 共用。

## 配置类

### BaseConfig
基础配置类，所有配置类的父类。

```python
from shared import BaseConfig

config = BaseConfig()
print(config.APP_NAME)  # "基金跟踪器"
print(config.APP_VERSION)  # "2.0.0"
```

### FundConfig
基金数据配置，包含基金列表、筛选阈值、数据源等。

```python
from shared import get_fund_config

fund_config = get_fund_config()
print(fund_config.DEFAULT_FUNDS)  # 默认基金列表
print(fund_config.SCREEN_UP)  # 上涨筛选条件
print(fund_config.REQUEST_TIMEOUT)  # 请求超时时间
```

### ChartConfig
图表配置，包含时间范围、颜色、基准指数等。

```python
from shared import get_chart_config

chart_config = get_chart_config()
print(chart_config.TIME_RANGES)  # 时间范围选项
print(chart_config.COLORS)  # 颜色配置
print(chart_config.BENCHMARKS)  # 基准指数
```

### PlotConfig
绘图配置（用于 fund_core.py）。

```python
from shared import get_plot_config

plot_config = get_plot_config()
print(plot_config.PLOT_MODE)  # 绘图模式
print(plot_config.PLOT_RANGE)  # 时间范围
```

### ServerConfig
服务器配置（用于 fund-tracker/backend）。

```python
from shared import get_server_config

server_config = get_server_config()
print(server_config.HOST)  # 服务器地址
print(server_config.PORT)  # 服务器端口
print(server_config.DATABASE_URL)  # 数据库URL
```

### OcrConfig
OCR 配置。

```python
from shared import get_ocr_config

ocr_config = get_ocr_config()
print(ocr_config.OCR_LANG)  # OCR 语言
print(ocr_config.MAX_FILE_SIZE)  # 最大文件大小
```

## 环境变量

所有配置都支持从环境变量读取，优先级高于默认值。

### 通用配置

| 环境变量 | 说明 | 默认值 |
|---------|------|---------|
| `DEBUG` | 调试模式 | `false` |
| `ENV` | 环境名称 | `development` |

### 服务器配置

| 环境变量 | 说明 | 默认值 |
|---------|------|---------|
| `HOST` | 服务器地址 | `0.0.0.0` |
| `PORT` | 服务器端口 | `8001` |
| `CORS_ORIGINS` | CORS 允许的来源 | `http://localhost:5173,http://localhost:8000` |
| `DATABASE_URL` | 数据库 URL | `sqlite:///./fundtracker.db` |
| `REDIS_URL` | Redis URL | `redis://localhost:6379/0` |
| `SECRET_KEY` | JWT 密钥 | （生产环境必须设置） |
| `WECHAT_APPID` | 微信 AppID | `` |
| `WECHAT_SECRET` | 微信 Secret | `` |

## 配置验证

配置加载时会自动验证，如果配置无效会抛出异常。

```python
from shared import validate_config, get_server_config

config = get_server_config()
errors = validate_config(config)
if errors:
    print(f"配置错误: {'; '.join(errors)}")
```

## 向后兼容

为了保持向后兼容，提供了 `CONFIG` 字典：

```python
from shared import CONFIG

# 与 fund_core.py 中的 CONFIG 完全兼容
print(CONFIG["file_path"])
print(CONFIG["default_funds"])
print(CONFIG["screen_up"])
```

## 配置重载

支持动态重载配置：

```python
from shared import ConfigLoader

# 重载所有配置
ConfigLoader.reload()

# 获取新配置
fund_config = get_fund_config()
```

## 使用示例

### 在 fund_core.py 中使用

```python
from shared import CONFIG

# 直接使用 CONFIG（向后兼容）
codes = CONFIG["default_funds"]
```

### 在 fund-tracker/backend 中使用

```python
from app.config import fund_config, chart_config

# 使用配置对象
default_funds = fund_config.DEFAULT_FUNDS
time_ranges = chart_config.TIME_RANGES
```

### 在 fund-tracker-desktop 中使用

```typescript
// 从环境变量读取
const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001/api/v1'
```

## 最佳实践

1. **优先使用环境变量**: 生产环境应通过环境变量配置敏感信息
2. **使用配置验证**: 启动时验证配置，避免运行时错误
3. **保持向后兼容**: 新项目使用配置对象，旧项目使用 CONFIG 字典
4. **文档化配置**: 在 .env.example 中说明所有可配置项

## 故障排查

### ImportError: No module named 'shared'

确保 `shared/` 目录在 Python 路径中：

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### 配置验证失败

检查环境变量是否正确设置：

```bash
echo $DEBUG
echo $SECRET_KEY
echo $DATABASE_URL
```

### 配置未生效

尝试重载配置：

```python
from shared import ConfigLoader
ConfigLoader.reload()
```