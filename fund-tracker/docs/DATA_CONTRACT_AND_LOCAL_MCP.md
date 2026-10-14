# 共享数据契约与桌面本地 MCP

> 实现日期：2026-10-14。只做现有数据核心分层和桌面只读 MCP，不接入收费源、不整套移植 OpenBB、不修改现有选价优先级。

## 一、两个独立交付

1. **共享数据核心**：在 backend/app 内，供 Web 和安卓使用；无 MCP/智能体 SDK 依赖。
2. **桌面 MCP 适配器**：位于独立 mcp-server，使用独立环境，经过本机 HTTP 消费后端 API。

~~~text
Web / Android ────────┐
                     ├── HTTP API → FundService / PortfolioService
AI host → stdio MCP ─┘                   ↓
                          DataSourceManager（采集、并发、快照、选择）
                                        ↓
                          provider_normalizers（纯 payload 标准化）
                                        ↓
                          data_contract（类型、能力、单位、质量）
~~~

安卓只包含共享后端 app 与 Web/Tauri 客户端；不会包含桌面 MCP 源码、入口、SDK 或独立环境。MCP 不能访问/修改数据库，不在后端启动过程中自动运行，不提供网络监听端口。

## 二、采集、标准化、选择的职责

- **data_contract.py**：FundDataResult 的唯一实现、提供商能力目录、报价类别/单位、时间规则与 QuoteQuality。data_source 保留旧公开名称的再导出，既有服务/诊断不用全部改导入路径。
- **provider_normalizers.py**：八种源 payload 的字段解析和标准化；不创建 Session，不做 HTTP，不读数据库或缓存。
- **data_source.py**：网络请求、超时、并发、后台增量快照和跨源净值校核。能力目录的 supports_batch 驱动批量/单只执行方式。
- **quote_policy.py**：仍是 auto/provider/nav 展示规则的权威位置。收盘和当日正式净值、平台估值、推算与 null 的原有行为保持。
- **history_data.py**：继续承担正式历史 NAV、累计净值和链式日收益口径；MCP 不另算一份历史/比较收益。

为了兼容既有使用方式，适配器 parse 方法是对纯标准化函数的薄委托，不保留第二份旧解析实现。

## 三、契约与质量说明

### 提供商能力

新增 GET /api/v1/funds/providers，返回 contract_version=1.0 和八个提供商的声明。该静态接口不触发外部请求，也不输出账号、Cookie、CSRF 或密钥。

字段包括 source、显示说明、upstream_family、data_kinds、supports_batch、price_unit、标准 change_unit、native_change_unit、timezone 和 requires_credentials。

- 天天、东方财富移动端、lsjz、pingzhongdata 归为已知 Eastmoney 服务上游，不能算四家独立供应商。
- Dayfund/Fund123 底层供应链未核实，upstream_family 为 null，不假造独立性。
- Fund123 原始比例为 ratio，标准化后为 percent；1 表示 1%，不是 0.01。

### 报价 quality

实时单/批查询和来源对比增加 quality；旧价格、状态等字段保留。

| 字段 | 含义 |
|---|---|
| contract_version | 质量契约版本，当前 1.0 |
| value_source / upstream_family | 当前展示值的真实来源及已知上游 |
| price_basis | unit_nav / provider_estimate / inferred_unit_nav / unavailable |
| price_unit / currency | 每份计价；未取得源端币种就保持 null，不擅自断言人民币 |
| change_unit / timezone | 百分数；上海时区 |
| source_time | 源端估值时刻或正式净值所属日，不是请求完成时间 |
| fetched_at / assessed_at | 数据获取时刻 / 本次质量说明评估时刻 |
| nav_date / nav_source | 基准正式单位净值的日期与来源，独立于估值源 |
| availability / freshness | 可用/不可用/不支持/采集中；当前估值、参考、日频净值或陈旧 |
| nav_age_calendar_days | 基准距请求日的自然日数；不是遗漏交易日数 |
| warnings / pending_sources | 稳定警告代码和解释，以及尚未完成的源 |

正式净值来源新增独立追踪字段 previous_nav_source / official_nav_source。新浪估值和天天正式净值合并后，两种来源不会混作一个。auto/nav/provider 选择完成后再生成质量说明，避免切换到正式净值后还残留“平台估值”的质量标签。

质量不是准确度评分、置信概率或 SLA。平台估值、持仓推算、未知基准日、较旧基准和未核实上游均明确解释。缺少行情不会用累计净值、成本价、零收益或合成数据补齐。

### 前端

首页基金详情和来源对比显示后端质量说明，区分源时刻和获取时刻。人工切换数据源采用该源的 quality；人工持仓/关联参考不继承之前平台估值的质量快照，避免错误归因。离线缓存仍是历史快照，不能从缓存日期宣称当前报价新鲜。

## 四、本地 MCP

详见 [MCP 使用说明](../mcp-server/README.md)。官方 SDK 固定 mcp==2.3.0；没有引入独立 FastMCP 框架。

六个只读工具：get_quotes、get_history、compare_funds、get_portfolio、get_data_sources、get_provider_catalog。参数是有限的基金代码/区间/口径，不开放任意 URL、SQL 或写操作。

使用独立 fund-tracker-mcp 环境，是因为安装预检会升级现有后端环境的多项依赖。后端继续保留 fund-tracker 环境原版本；未使用/修改 base 环境。

服务只提供 stdio；后端 URL 强制环回、忽略系统代理、拒绝重定向。已知后端故障转为可解释 MCP 错误，未知异常由 SDK 隐藏细节。连接客户端需要用户选择，未自动修改任何 AI 客户端的全局 MCP 配置。

## 五、安卓隔离的自动守卫

MCP 测试检查：

1. 后端和安卓 Python 入口无 mcp/mcp_types/fastmcp/fund_tracker_mcp 导入。
2. backend requirements 与 requirements-android 没有桌面 SDK。
3. Gradle Python 同步根是 backend，仅 include app/**，不包含同级 mcp-server。
4. MCP 发布包仅包含 fund_tracker_mcp，不引入 backend app、FastAPI、SQLAlchemy、pandas 或 AKShare。

这是对当前构建配置/依赖的明确证明，不代替 APK 编译、安装和设备运行验收。本项没有生成新 APK，也没有改动其他正在进行的安卓封装任务。

## 六、验证入口

- 后端：既有 fund-tracker 环境，python -B -m pytest -m "not integration and not slow" -q。
- MCP：独立 fund-tracker-mcp 环境，在 mcp-server 执行 python -B -m pytest -p no:cacheprovider。
- 前端：npm run test、npm run type-check、npm run build。
- 既有源专项：data-source-test/tests/test_realtime_benchmark.py。

测试数据、MockTransport 和测试 HTTP 服务只在测试中使用，未加到开发/生产回退路径。

### 本次结果

- 后端非 integration/slow 套件：139 项通过，5 项 integration 未执行。
- MCP：43 项通过，含真实 stdio 子进程与五项架构/打包边界检查。
- 前端：23 项测试、类型检查、生产构建及涉及文件 oxlint/eslint 通过；既有 Element Plus/ECharts 大包警告仍在。
- 既有实时源专项离线测试：9 项通过。
- 实际本机后端联调：通过真实 stdio MCP 查询能力目录（1.0、8 源）及 161725 手动正式净值；保留 2026-10-13 净值日、源端来源和 null 币种，没有伪造价格或日期。
- 再次验证后端 Python 3.11.15 / FastAPI 0.136.3 / Pydantic 2.13.4 / HTTPX 0.28.1 未被 SDK 安装升级。
- 未修改 AI 客户端全局配置，未生成新 APK。
