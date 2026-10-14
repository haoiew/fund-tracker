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
| source | 数据源 key：`sina`、`tiantian`、`dayfund`、`fund123`、`eastmoney_mobile`、`tencent`、`eastmoney_lsjz`、`pingzhongdata`；八条接口不代表八个独立实时估值供应商 |
| display_name / short_name | 中文展示名 |
| estimate_nav / estimate_change_pct | 该数据源返回的净值或涨跌幅 |
| update_time | 盘中估算时刻或最新净值日期 |
| last_nav / last_nav_date / last_change_pct | 独立保存的正式单位净值、净值日期与来源日增长率；缺失的正式日增长率不以盘中涨跌或简单 NAV 比值补造 |
| data_kind_label | `实时估值`、`最新净值`、`过期估值` 或 `采集中` |
| is_realtime / is_fresh | 是否为满足当前时效检查的源端估值，不表示正式净值的本次可用性 |
| is_pending | 尚未返回；不是失败，不可人工采用尚无价格的行 |
| priority | 有效估值采用顺序，不是请求先后顺序 |
| fetch_started_at / fetch_duration_ms | 本次实际源请求的启动时刻及耗时（ms），与源端行情时刻不同 |
| is_available | 本次是否取得有效数据；有效的旧净值可以为 true，但不属于实时估值 |
| data_timestamp | 抓取时间，不能替代 `update_time` 的实际行情时刻或净值日期 |

顶层 `total_sources` 为本次有效接口数量（包括正式净值），`realtime_sources` 为满足时效/一致性校核的实时估值数量。两者不可混同；候选同日单位净值与正式净值明显冲突时，不作为可采用估值。顶层 `pending_sources/primary_source_complete` 描述本轮采集进度，未全部返回的对比是当前快照，不是最终完整清单。

### 报价显示策略

`GET /funds/realtime/{code}` 和 `POST /funds/realtime/batch` 支持查询参数 `view` 和 `refresh`（bool，默认 false）：

源端估值优先级为 **新浪 → 天天 POST → Dayfund → Fund123**；四源及正式净值接口同时启动。响应返回当前已完成部分，不等所有来源；较低优先级暂定值可被后来返回的有效高优先级值替换。无有效外部估值且全部估值源已完成后才自动推算。正式单位净值口径保持独立。新浪字段、可用性与授权边界见[备用源核查](ESTIMATE_FALLBACK_20261014.md)。

| view | 行为 |
|---|---|
| auto（默认） | 上海时间 15:00 后且正式净值日期为当天时显示正式净值；否则优先当前源端估值，无估值时使用有有效时间戳的披露持仓/关联标的推测；均不可用则返回空估值 |
| provider | 只返回当前源端估值，缺失时空估值，不推测，不自动选净值 |
| nav | 手动返回最新公布的正式单位净值，同时保留真实公布日期，不要求是今天 |

`data_kind` 为 `realtime_estimate/latest_nav/holdings_estimate/reference_symbol_estimate/unavailable`。
`is_inferred=true` 标识推测，不属于 `is_realtime=true` 的源端估值。
`official_nav/official_change/official_update_time` 保留正式净值证据，即使当前显示估值为空也可供手动查询。
`estimation_details` 含基准净值及日期、真实行情时刻、披露持仓日、已报价披露持仓覆盖率及其占基金净值比例、外推假设和跨日/汇率限制；覆盖率 100% 不代表全基金资产已计价。
缺失估值时 `estimate_nav/estimate_change` 为 null，`data_kind=unavailable`；不要在调用方填 0 或成本价。货币基金收益不进入单位净值计价路径。
批量请求去重后保留输入首次出现的顺序。单只/批量/来源对比共用 60 秒源快照缓存；`refresh=true` 启动新一轮全源采集，正在运行的同代码任务共享。Web 启动/刷新用 true，后台进度读取用 false，不重新请求上游。每行 `pending_sources` 列出仍在采集的源，`primary_source_complete=true` 表示新浪已成功、无值或明确失败（不等于有估值）；界面此时结束主加载，继续后台补齐。单来源整批采集预算 8 秒、单代码接口每源并发 2 个。默认时效阈值 900 秒，午休/收盘后按最近交易时段判断，完整跨市场节假日语义尚待扩展。

历史 `/funds/{code}/history` 的 `data.data.value_basis=unit_nav`，`values` 为单位净值，`changes` 为来源日增长率（%），缺失时为单位净值价格变动。对比结果 `funds[].return_basis` 标明来源日增长率或混合价格变动口径，不能将所有输出无条件视为分红再投总收益。

基金及基准对比的 `changes` 是绘图用的区间累计曲线，**不是每日收益数组，禁止再次逐点复利**。
`returns` 给出 `d3/d7/d30/m3/m6/y1/y3/y5` 日历区间收益；按各序列最近观测日回溯，非观测日取截止日之前最近有效基准，`return_period_dates` 明示实际起止日，`period_basis=calendar_ending_at_last_observation`。统计使用可用全历史，`range` 只控制图表窗口；没有所需基准时该统计为 null，不能填 0。基准指数的 `return_basis=index_price_change`。
Decimal 字段在 JSON 中可能为字符串，数值使用前按字段转换，基金代码等标识不能统一转换为数字。
兼容字段 `fallback_estimate` 保持 null，原“昨天净值涨跌当今日估值”的逻辑已移除。

## 持仓 API (`/portfolio`)

持仓报价沿用 `auto` 口径。只要任一正份额持仓缺少有效报价，组合总市值、总盈亏及总收益率返回 null，已知投入成本仍保留；汇总的 `unpriced_count/unpriced_codes` 说明缺项，单项当前市值/盈亏也为 null。零份额持仓的当前价值为 0，无需报价。调用方应显示未知，而不是补造部分合计。

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

`GET /portfolio/summary?include_quotes=false` 只返回本地持仓输入及成本统计，不访问行情源或远程名称目录；正份额持仓的报价/市值/收益为 null，零份额当前价值为 0。默认 `include_quotes=true` 保持原有行情汇总行为。Web 初始化使用无报价汇总，再对关注/持仓去重代码先请求 `view=provider&refresh=true`，有返回结果即显示；新浪完成后结束主加载，后台读取同轮快照，外部估值均明确后才补充必要的 `view=auto`；历史图表仍按需加载。

`POST /portfolio/refresh` 强制启动全源采集，组合只按当前已有报价汇总；需要读取来源进度时，查询 `/funds/realtime/batch` 的 `primary_source_complete/pending_sources`，不要把组合价格缺项当成全源最终失败。

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

## 数据契约与质量元数据（兼容扩展）

GET /api/v1/funds/providers 返回静态 contract_version 与 providers 能力目录，不请求外部数据，不返回凭证。

实时单/批结果及 data-sources 的每个来源增加 quality，包含值来源/已知上游、单位（币种未知为 null）、源时刻/获取和评估时刻、正式净值基准日/来源、可用性/时效/警告。旧价格和选价参数不变；quality 不代表准确度或服务等级保证。详情见 [共享数据契约与本地 MCP](DATA_CONTRACT_AND_LOCAL_MCP.md)。

桌面 MCP 是独立 HTTP 消费者，不是嵌入此 API 的 MCP 路由，也不是安卓组件；不开放持仓/自选/设置写工具。
