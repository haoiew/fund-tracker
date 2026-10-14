# 本地 Fund Tracker MCP（桌面独立组件）

这是独立的 **stdio MCP 程序**，采用官方 Python SDK `mcp==2.3.0`。它通过本机后端 HTTP API 提供六个明确的只读工具，不读取数据库、不启动后端、不实现第二份基金算法。

## 架构与安卓边界

`AI 客户端 → 本地 stdio MCP → 环回 HTTP API → 共享后端业务/数据契约`

- 源码只在此目录 `mcp-server/`，与 `backend/`、`frontend/` 平级。
- SDK 依赖只在此目录的 `pyproject.toml` / `environment.yml` 中。
- 后端、前端和安卓没有导入本包；安卓 Gradle 只同步 `backend/app/**`，独立安卓 requirements 没有 MCP SDK。
- 后端、Web、安卓共用的数据契约不含任何 MCP 依赖；MCP 本身不被复制到 APK。
- `tests/test_packaging_boundary.py` 自动检查上述边界。配置检查不等于已构建或安装新 APK。

## 环境

使用独立命名环境，不安装到 Miniforge base，不升级现有后端环境。

若尚未创建环境：`mamba env create -f environment.yml`。

本次已创建 `fund-tracker-mcp`，后端继续使用既有 `fund-tracker`。可在加载 profile 的 PowerShell 中激活后运行，或者使用 Miniforge 的绝对 conda.exe 路径执行 `run --no-capture-output -n fund-tracker-mcp ...`。无需安装本地包，直接运行 `run.py`。

## 启动和客户端配置

1. 按项目现有方式启动本机后端，默认 `http://127.0.0.1:8001/api/v1`。
2. 在 MCP 环境中运行 `python -B run.py --print-client-config`，得到当前解释器和入口的绝对路径 JSON。
3. 将 JSON 添加到可信且支持 stdio MCP 的客户端。由客户端启动此程序；正常 stdio 模式不向 stdout 打印提示或日志。

本机已验证的 PowerShell 命令：

~~~powershell
& 'C:/Users/138721/.local/share/mamba/envs/fund-tracker-mcp/python.exe' -B 'D:/workdir/code/Explore/fund-tracker/mcp-server/run.py' --print-client-config
~~~

默认启动参数不包含 `--print-client-config`，程序将进入 stdio 协议模式。这个模式不是供浏览器访问的网页服务。

### 配置

| 参数/环境变量 | 默认值 | 约束 |
|---|---|---|
| `--api-url` / `FUND_TRACKER_API_URL` | `http://127.0.0.1:8001/api/v1` | 只允许 localhost、127.x 或 ::1 环回地址；禁止凭证、查询和片段 |
| `--timeout` / `FUND_TRACKER_MCP_TIMEOUT` | 65 秒 | 1–120 秒；连接超时 5 秒 |

显式参数优先于环境变量。HTTP 客户端忽略系统代理环境变量，不跟随重定向；不会将本机请求或响应转发到其他地址。MCP 不读取后端 .env 或供应商凭证。

## 工具

| 名称 | 参数 | 复用的 HTTP 路径 |
|---|---|---|
| `get_quotes` | 1–50 个六位代码；auto/provider/nav | POST /funds/realtime/batch |
| `get_history` | 六位代码；时间范围 | GET /funds/{code}/history |
| `compare_funds` | 1–10 个代码；范围；是否含基准 | POST /funds/compare |
| `get_portfolio` | include_quotes 默认 false | GET /portfolio/summary |
| `get_data_sources` | 六位代码 | GET /funds/{code}/data-sources |
| `get_provider_catalog` | 无 | GET /funds/providers |

范围仅允许后端现有 `1W/1M/3M/6M/1Y/ALL`，不把未支持范围默默变成 3M。代码保留前导零，输入重复代码会去重。

这里两条 POST 是查询 API，不修改持仓、自选、交易或配置。后端查询可能更新行情/历史缓存，这是现有后端生命周期，不等于 MCP 开放了业务写操作。没有删除、导入确认、修改设置、通用 URL 请求等工具；只读 annotations 之外还有实际工具白名单。

## 数据与错误

- 质量字段、正式净值所属日、来源时刻、获取时刻和收益口径由后端给出；本组件原样保留，不重算收益或填造价格。
- quote null 保持 null；采集中与数据不可用由后端字段/quality 区分。
- 后端未运行、超时、错误 HTTP 状态、非 JSON 或无效响应，返回 MCP `is_error=True`，不伪装成空数据成功。
- 只向模型暴露经过本组件清洗的已知错误；不反射原始响应体、密钥或请求 URL。
- 持仓是敏感数据。连接 AI 客户端后，工具结果可能交给该客户端使用的模型；仅向可信客户端提供本机能力。

## 验证

在 MCP 环境和本目录执行 `python -B -m pytest -p no:cacheprovider`。

测试包括工具发现、schema 和数量限制、错误和代理/重定向保护、真实 stdio 子进程握手/调用及 APK 隔离。模拟 HTTP 和数据只出现在 tests/ 内。生产没有假数据或离线模拟回退。

更多共享数据契约说明见 [数据契约与本地 MCP 架构](../docs/DATA_CONTRACT_AND_LOCAL_MCP.md)。
