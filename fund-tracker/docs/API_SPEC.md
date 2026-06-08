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
| GET | /funds/{code}/data-sources | 获取单只基金各数据源估值对比 |
| GET | /funds/{code}/history?range=3M | 获取历史净值 |
| POST | /funds/history/batch | 批量获取历史数据 |
| POST | /funds/search | 搜索基金 |
| POST | /funds/screen/up | 筛选连续上涨 |
| POST | /funds/screen/down | 筛选连续下跌 |
| GET | /funds/screen/{direction} | 筛选（简化） |
| POST | /funds/compare | 基金对比 |
| POST | /funds/compare/multi | 多周期对比 |
| POST | /funds/info/batch | 批量获取基金信息 |

### `/funds/{code}/data-sources` 响应要点

`sources[]` 会返回数据源英文 key 和中文展示信息：

| 字段 | 说明 |
|------|------|
| source | 数据源 key，如 `tiantian`、`efinance`、`tencent`、`eastmoney_lsjz`、`pingzhongdata` |
| display_name / short_name | 中文展示名 |
| estimate_nav / estimate_change_pct | 该数据源返回的净值或涨跌幅 |
| update_time | 盘中估算时刻或最新净值日期 |
| data_kind_label | `实时估值` 或 `最新净值` |
| is_realtime | 是否为带盘中时刻的实时估值 |
| is_fresh | 该数据源本次是否可用 |

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
| POST | /portfolio/ai-connection-test | 测试 OpenAI 兼容接口，可选图片输入检测 |
| POST | /portfolio/ai-recognize | AI 识别持仓截图并匹配基金代码 |
| POST | /portfolio/import/preview | 导入预检，计算可导入/需核对条目 |
| POST | /portfolio/import/confirm | 确认导入预检通过的持仓 |

### AI 持仓导入流程

1. `POST /portfolio/ai-connection-test`：请求字段为 `model`、`base_url`、`api_key`、`include_vision`。`include_vision=true` 时会同时发送测试图片，响应包含 `latency_ms` 和 `vision_latency_ms`。
2. `POST /portfolio/ai-recognize`：提交 `image_base64`、模型配置和可选 `prompt`，返回 `holdings[]`、`expected_count`、`warnings[]` 和候选基金匹配信息。
3. `POST /portfolio/import/preview`：提交识别结果，返回 `ready_count`、`skipped_count`、`invalid_count` 和每行导入原因。
4. `POST /portfolio/import/confirm`：按预检结果写入本地持仓，返回每行 `success/skipped/failed` 状态。

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
