# API规范

## 基础信息

- Base URL: `http://127.0.0.1:8001/api/v1`
- 响应格式: `ResponseModel { code, message, data }`
- 认证: 无（本地单用户工具）

## 基金 API (`/funds`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /funds/list | 获取基金列表 |
| POST | /funds/list/add?code=xxx | 添加基金 |
| POST | /funds/list/remove?code=xxx | 移除基金 |
| GET | /funds/realtime/{code} | 获取单只实时数据 |
| POST | /funds/realtime/batch | 批量获取实时数据 |
| GET | /funds/{code}/history?range=3M | 获取历史净值 |
| POST | /funds/history/batch | 批量获取历史数据 |
| POST | /funds/search | 搜索基金 |
| POST | /funds/screen/up | 筛选连续上涨 |
| POST | /funds/screen/down | 筛选连续下跌 |
| GET | /funds/screen/{direction} | 筛选（简化） |
| POST | /funds/compare | 基金对比 |
| POST | /funds/compare/multi | 多周期对比 |
| POST | /funds/info/batch | 批量获取基金信息 |

## 持仓 API (`/portfolio`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /portfolio | 获取所有持仓 |
| POST | /portfolio | 创建持仓 |
| GET | /portfolio/profit | 获取收益统计 |
| GET | /portfolio/summary | 获取汇总 |
| GET | /portfolio/{id} | 获取单个持仓 |
| PUT | /portfolio/{id} | 更新持仓 |
| DELETE | /portfolio/{id} | 删除持仓 |
| POST | /portfolio/refresh | 刷新持仓数据 |

## 系统 API (`/system`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /system/health | 健康检查 |
| GET | /system/cache/stats | 缓存统计 |
| GET | /system/scheduler/status | 调度器状态 |
| POST | /system/scheduler/refresh | 手动刷新 |
| POST | /system/scheduler/history/update | 更新历史数据 |

## 时间范围参数

| 值 | 说明 | 天数 |
|---|---|---|
| 1W | 近1周 | 7 |
| 1M | 近1月 | 30 |
| 3M | 近3月 | 90 |
| 6M | 近6月 | 180 |
| 1Y | 近1年 | 365 |
| ALL | 全部 | 0 |
