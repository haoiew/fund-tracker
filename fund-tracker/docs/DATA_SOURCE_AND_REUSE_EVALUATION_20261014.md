# 授权数据源与开源项目复用评估

> 核查日期：2026-10-14（Asia/Shanghai）。范围：同花顺 iFinD/QuantAPI、Tushare Pro，以及 AKShare、efinance、Leek Fund、OpenBB、FastMCP、MCP Python SDK。
> 本文是评估，不是实施批准；未注册账号、未采购、未请求付费业务数据、未安装依赖、未移植第三方代码。官方公开文档与源码事实、当前仓库观察和工程建议分别陈述；没有用 Star/Fork 推导数据质量。

## 一、先看决策

1. **同花顺有“免费接口档”，但不能据此承诺一个从未购买 iFinD 的新用户可以零成本获得全部所需 API。** 官方权限页说持 iFinD 账号即可使用免费档；官方 FAQ 同时把免费账号解释为购买终端后附带少量接口权限。新账号资格、HTTP token 以及基金实时估值函数权限，需要向官方确认或登录验收。[S1][S2]
2. **Tushare Pro 最适合低成本补充正式净值和基金资料，不应被当作场外主动基金盘中估值替代品。** fund_nav 要求至少 2000 积分；公开价 200 元/年对应该积分档。ETF 实时成交数据、ETF IOPV 则是另行付费的数据类型。[S5][S6][S7][S8]
3. **当前收益最大的复用方向：完善现有数据契约和采集/转换边界，复用披露持仓做组合穿透分析，再增加阈值跨越提醒。** 前两项分别参考 OpenBB 的提供商分层、AKShare 的基金披露接口；提醒参考 Leek Fund 的上次/本次比较思路。这里的优先级是针对当前项目的工程判断，不是已测性能或收益率。
4. **若目标包含“让 AI 调用本项目”，再选一个 MCP 实现层。** 少量精确定义的工具可用官方 SDK；若需要 FastAPI 转接、组合、鉴权和交互式 MCP Apps，可评估 FastMCP。两者不提供基金数据，也不需要作为两个平级框架重复安装。[S16][S17][S18]
5. **不建议整套迁入 OpenBB、不建议恢复 efinance 默认计价、不建议把 Leek Fund 的行情/盈亏实现直接替换当前核心。** 当前项目已具备多源、单批共享路径、时效和价格类别判断；移植应补缺口，而不是退回另一套粗略规则。

## 二、先区分数据口径

- **正式单位净值（NAV，元/份）**：基金管理人公布的每份资产净值，必须带净值所属日期。公告日和净值日不是一个概念。
- **盘中估算净值（通常元/份）**：数据平台按模型估算的当日值，不等于基金管理人已确认的正式净值，也不是保证可成交的价格。
- **累计净值**：在单位净值之外累计考虑分红等调整的披露指标；不应拿它直接乘当前份额计算可赎回市值。复权净值则还涉及约定的收益再投资/调整口径，不能把累计、单位和复权净值混为同一列。
- **ETF 成交价 / IOPV（通常元/份）**：前者是交易所实际买卖形成的价格；后者是盘中基金资产参考价值。两者可存在溢折价，都不能直接当作另一只场外联接基金或主动基金的正式净值。[S3][S6][S8]

## 三、同花顺 iFinD / QuantAPI

### 定位与接入条件

iFinD 是同花顺金融数据产品，QuantAPI 是其程序化数据接口。官方提供多语言 SDK 和 HTTP API，二者是调用方式，不是两家独立数据供应商。SDK 要有接口账号并登录；HTTP 示例以 refresh_token 获取 access_token，然后调用业务接口。已有普通行情 App 账号不应直接假定等于获得 QuantAPI 数据权限。[S2][S3][S4]

建议接入步骤：

1. 确认账号及所需数据产品权限，明确是否已有 iFinD 终端权益。
2. 为 HTTP 调用取得有效 token；若免费档不支持该渠道，不能仅凭 SDK 可登录就推定 HTTP 可用。
3. 用官方代码表或客户端指标查询生成请求，区分 .OF 等场外基金与 .SH/.SZ 场内证券。
4. 后端保管凭证，实现 token 生命周期、超时、额度控制和业务错误检查；前端不直接持密钥。官方 FAQ 还列 SDK 同时仅一台设备登录、HTTP 可绑定 20 个 IP；access_token 有效期 7 天，账号级 QPS 上限 20（单函数通常 10），实施时须按实际账号规则验收。[S2]
5. 通过真实基金清单验收后，再在现有 DataSourceManager 中增加有限适配器，不改写报价选择规则。

第 4、5 项是本项目建议，不表示已实现。

### 免费档、试用与价格

官方免费档公布的主要额度如下；“条”指指标单元格，不是一次 HTTP 请求：[S1]

| 数据类别 | 免费档额度 | 免费档主要历史跨度 |
|---|---:|---|
| 实时行情 | 300 万单元格/月 | 实时取值 |
| 历史行情 | 100 万单元格/月 | 最近 5 年 |
| 高频序列 | 150 万单元格/月 | 最近 1 年 |
| 日期序列、基础数据、专题报表 | 各 60 万单元格/月 | 日期序列/基础数据最近 5 年 |
| 日内快照 | 200 万单元格/月 | 最近 3 个月，交易所范围另有限制 |

**账号资格仍有重要不确定性：** 权限页描述账号即可登录，FAQ 描述购买终端附带的免费接口；这可能是产品档位或文档表述差异，不能擅自选择一个解释。需要官方回答“从未购买终端的个人能否长期免费使用，以及基金实时估值是否包含”。[S1][S2]

官网提供申请试用入口和试用额度，但本次没有查到统一公开的正式版人民币报价、固定试用天数或该基金估值函数的独立价格。采购应要求针对所需基金范围、HTTP 机器调用、并发/频次、历史跨度和展示授权的书面报价，不能拿第三方传言作为价格证据。[S1][S2]

### 对当前项目的价值与采购门槛

官方确有 THS_realTimeValuation 以及 HTTP /api/v1/fund_valuation；可请求最新点或当日分时。**文档演示使用证券 ETF 512880.SH，并没有因此证明本项目主动场外基金/QDII 的覆盖，也未明确该函数是否纳入免费档。**[S3]

试用清单可复用已有诊断样本：015916、018125、015790、519674、160125、017093、161226，并加入现有场内 ETF。验收应记录：

- 真实返回的单位/估值类别、净值基准日期和估值时刻，而不仅是 HTTP 200；
- 场外主动基金、QDII、ETF 各自覆盖率，空值和不支持错误；
- 国内外交易时段的更新频率与陈旧情况；
- 同一基金、同一所属日期对齐后，正式 NAV 公布时的估值误差；
- 免费/试用权限、消耗额度、HTTP token 条件和未来对外展示许可。

**工程结论：先确认免费资格或申请定向试用，验证它能补当前缺口，再考虑付费。没有账户实测证据时，不能承诺收费后估值就更准确、更稳定或全覆盖。**

## 四、Tushare Pro

### 定位、权限和价格

Tushare Pro 是统一数据服务平台；注册后获取个人 token，可用 Python SDK 或 HTTP 调用。积分是接口资格门槛，不是每请求一次消耗一定积分；付费积分/独立权限有有效期，仍须遵守接口频次和行数限制。[S5][S9][S10]

| 档位 | 官方价格 | 公开总表频次 | 与本项目关系 |
|---|---:|---:|---|
| 120 积分免费档 | 0 元 | 50 次/分钟 | 总表主要列非复权日线；不足以调用 fund_nav |
| 2000 积分档 | 200 元/年 | 200 次/分钟 | fund_nav 门槛至少 2000，可评估正式净值补充 |
| 5000 积分档 | 500 元/年 | 500 次/分钟 | 常规数据更高频次/总量权益 |
| 10000 积分档 | 1000 元/年 | 常规 500 次/分钟 | 部分特色数据另有频次 |
| 15000 积分档 | 1500 元/年 | 500 次/分钟 | 更多特色权限 |

以上摘自权限总表；最终须同时满足具体接口规定，不能以总表代替每个 API 的门槛。[S5]

基金相关独立权限例子：[S5][S7][S8]

- ETF 实时日线成交：200 元/月。
- ETF 实时参考（含 IOPV / 申赎指标）：300 元/月；当前示例 rt_etf_sz_iopv 是深市 ETF，不据此推定全部市场覆盖。
- 这些不包含在 200 元/年的普通积分档里，也不是场外主动基金实时估值服务。

### 免费账号能做什么

可以免费注册。积分规则列注册 100 分、完善真实资料 20 分；贡献代码、反馈、文章等经确认也可加分。高校师生有身份确认后的免费权限路径，服务协议列学生 2000、教师 5000 积分。**注册赠分不是直接赠送完整基金净值 API；符合资格且达到门槛后，才可能免费使用相应接口。**[S9][S10]

fund_nav 提供 unit_nav、accum_nav、adj_nav、nav_date、ann_date 等，适合正式净值核对、历史补充和分红复权分析；它不是盘中估值接口。Tushare 有实时 ETF 等产品，所以也不能反过来笼统说整个 Tushare 都不提供实时数据。[S6][S7][S8]

服务协议明确限定个人、非商业用途和个人查看，并禁止共享账号。若以后将网站面向其他人、商业运营或再分发数据，须另确认授权；“个人接口付费”不自动意味着获得任意对外供数许可。[S10]

### 现有仓库适配器不能直接上线

当前测试适配器 data-source-test/sources/tushare_source.py 存在需要重新核对的实现：

- 按基金代码首位机械补 .SH/.SZ，无法正确覆盖全部场外基金身份，应查询官方基金列表建立映射；
- fund_nav 写死 market='E'，而官方还有场外 'O'；
- 用 end_date 排序和取日期，与 fund_nav 文档输出 nav_date 不一致；
- 批量查询固定每只间隔 65 秒，来自旧“每分钟一次”假设，不应作为当前积分档的通用限制；
- 净值相邻比值只是单位净值价格变化，分红/拆分日不能自动当作完整投资收益率。

以上是只读代码审查，没有改动该适配器。接入时仍需真实 token 验收、按日期归一和现有 history_data 口径处理。[S5][S6]

**工程结论：个人历史分析可先评估 200 元/年的门槛；不为修复场外盘中估值缺口而购买它。若仅现有免费正式净值足以满足需求，也没有必须新增收费依赖的理由。**

## 五、图 2 六个项目逐一说明

### 1. AKShare：金融数据采集库

**是什么/怎么实现：** Python 函数封装多个公开上游，执行 HTTP 获取、解析和字段转换，常返回 pandas DataFrame。它是数据接入工具，不是一款基金持仓软件，也不是它自己生成所有金融数据。[S11]

**GUI：** 核心库没有完整基金管理 GUI；Notebook、示例图和 AKTools HTTP 封装不等于现成业务界面。[S11]

**本项目已有：** requirements 和 FundService 已使用 AKShare 进行基金目录/历史/基准等查询，不能把“安装 AKShare”再当作新增能力。

**高价值可复用：**

- fund_portfolio_hold_em：披露股票持仓；
- fund_portfolio_bond_hold_em：披露债券持仓；
- fund_portfolio_industry_allocation_em：行业配置；
- fund_fh_em / fund_cf_em：分红/拆分事件。[S12][S13]

利用这些或现有 F10 披露持仓，可增加组合重合持股、行业集中度和事件解释。应复用现有持仓获取/日期缓存，而非再建立一套重复采集路径。股债持仓比例通常是占基金净资产百分比；只能按对应报告期展示，部分披露不等于实时完整持仓，也不能据此声称得到了精确盘中估值。

**复用方式：** 调已存在的依赖和有限函数，低到中成本；不复制整库。多个 Eastmoney 包装接口不构成多个独立供应商，新增元数据/历史接口也不能算成增加实时估值覆盖。[S12]

### 2. efinance：较轻量的数据包装库

**是什么/怎么实现：** Python 包，围绕基金/股票/债券/期货提供历史和批量查询，基金实现大量使用东方财富移动端数据。批量历史函数把单基金查询组合并发执行。[S14]

**GUI：** 核心库无基金管理 GUI；返回数据表或 Notebook 示例。

**可借鉴：** 清晰的领域函数组织、批量输入输出形式、持仓/阶段收益接口发现；请求封装需要按本项目超时、连接管理和错误策略改造。

**不能直接复制：** 本次固定版本源码 get_realtime_increase_rate 将 ACCNAV 映射为“最新净值”；get_quote_history 还可见 verify=False 以及缺少显式 timeout。当前项目已隔离单位/累计净值，不应把这些逻辑重新带回生产。[S14]

**收益判断：** 对当前项目增量较低；作为小范围接口参考即可，不恢复默认计价链，也不把它当新的独立行情供应商。

### 3. Leek Fund：有 GUI 的基金/行情应用

**是什么/怎么实现：** TypeScript 编写的 VS Code 生态扩展；使用编辑器侧边栏、状态栏、Webview 展示行情、基金走势、披露持仓和简易盈亏。当前 README 还区分基础功能和 Pro 的分组、完整资产管理等功能；不能把全部宣传功能都推定为可从开源目录无条件复制。[S15]

**GUI：** 有，但主要是编辑器内界面，不是拿来就能替换本项目的 Vue Web 前端。

**高价值参考：** 上次/本次报价比较触发阈值提醒；自选分组、紧凑摘要和有节制的刷新体验。src/shared/remindNotification.ts 是提醒候选；src/statusbar/、src/webview/ 是交互参考。[S15]

**迁移边界：** 提取纯判断/事件思路，再接本项目 Vue + Element Plus 的消息和现有存储。IDE commands/window、Webview 消息桥、React/TSX 页面不能直接搬到 Vue。增加提醒时本项目还应单独设计冷却、重复触发去重、过期/空值排除。

**不迁移：** 固定源码 src/explorer/fundService.ts 仍可见旧 fundgz/jsonpgz 查询，并把无效涨幅转换为 0 的展示处理；本项目不能因此放弃真实空值和新鲜度检查。其他产品的简单盈亏也不能替代本项目的份额、成本、交易和分红口径。[S15]

### 4. OpenBB：多提供商标准化数据平台

**是什么/怎么实现：** 开源数据集成层，将公开、授权或自有数据的不同提供商统一到模型和查询入口，可供 Python、REST、MCP 等消费。核心源码 Fetcher 显式分开 transform_query、extract_data 和 transform_data，Provider 声明凭证和模型对应的 fetcher；OBBject 承载结果、provider、warnings 和附加信息。[S19][S20][S21]

**GUI：** 生态有 OpenBB Workspace 图形工作台；官方将其与开源数据平台区分，Workspace 是界面产品，不应把仓库后台当作完整开源 GUI。当前仓库根许可证为 Apache-2.0，但它不授予各上游数据或另外的 Workspace 产品使用权。[S19][S22]

**最有价值的参考：** 把“参数适配—原始采集—标准化—选择/展示”分开；登记提供商能力、所需凭证与错误/警告；让 Web 和 MCP 消费同一业务核心。

**当前落点：** 围绕已有 FundDataResult、DataSourceManager、quote_policy 和 history_data 补足契约，不新建一套平行 OBBject 系统。明确 data_kind、单位、基金所属市场、source_time、NAV 日期、上游家族与陈旧原因。

**收益判断：** 参考架构收益高，整套依赖迁入成本高；未验证其默认提供商能补中国主动场外基金估值，不为 GUI 或 Star 数迁移。

### 5. FastMCP：完整 MCP 应用框架

**是什么/怎么实现：** 把普通 Python 函数包装为 MCP tools/resources/prompts，提供客户端、传输及框架能力；官方支持把 FastAPI 转为 MCP、或将 MCP 挂到 FastAPI。[S16][S17]

MCP 是向模型客户端提供工具/数据的协议，不是金融数据源或“自动分析基金”的模型。

**GUI：** 没有开箱即用的基金 GUI；有开发调试方式，当前还支持 MCP Apps，在支持该扩展的宿主里渲染表格、图表、表单等交互界面。它提供造界面的能力，不是替换现有 Vue 的必要条件；Apps 依赖还需按官方提醒固定兼容版本。[S18]

**项目价值：** 若要 AI 调用已有服务，可定义 get_quotes、get_history、compare_funds、get_portfolio 四类只读工具。优先精确工具，而非把全部 REST 自动暴露；持仓修改、截图确认导入、删除等写操作不应默认开放。

**复用方式：** 使用库而非复制源码；先本机 stdio，远程 Streamable HTTP 另做鉴权和授权。MCP 工具薄封装现有 service，不再写一份行情/收益计算核心。若没有 AI 工具接入目标，它对当前盘中估值覆盖没有直接收益。

### 6. MCP Python SDK：官方协议实现

**是什么/怎么实现：** MCP 官方 Python SDK，实现服务器/客户端、结构化工具参数与结果、资源和提示词、stdio/Streamable HTTP 等。当前官方文档有类型化函数和简洁注册例子，不能把它理解成必须手写全套协议。[S23]

**GUI：** 不是基金图形应用；MCP Inspector 是单独的开发调试界面，业务交互由宿主/应用实现。[S23]

**项目价值：** 同样可实现上述四类薄只读工具，适合协议边界清楚、框架附加需求较少的情况。SDK 和 FastMCP 需要依据目标二选一为主，不需要为了“多一层能力”同时维护两套业务适配器。不同主版本的教程/API 不可混用，实施前锁定包版本与当前 FastAPI/Pydantic 环境的兼容性。

## 六、建议的优先级与落地范围

以下是工程判断；低成本表示有限函数/纯逻辑适配，中成本包含模型、缓存/持久化及测试，高成本意味着框架迁移。不是工期承诺。

| 优先级 | 参考对象 | 明确增量 | 适配成本 | 不做什么 |
|---|---|---|---|---|
| P1 | OpenBB 架构 | 现有提供商能力登记、采集/标准化边界和质量说明 | 中 | 不迁移整个后台框架 |
| P1 | AKShare + 已有披露持仓 | 组合持仓重合、行业/股债暴露、分红拆分解释 | 低到中 | 不重复写已有获取器，不当实时全仓 |
| P2 | Leek Fund | 阈值跨越提醒、紧凑概览；分组按实际需求 | 低到中 | 不复制 IDE 组件/旧行情和空值归零逻辑 |
| 条件性 P1 | 官方 SDK 或 FastMCP | 4 类只读 MCP 工具，Web 与 AI 共用 service | 低到中 | 不放出全部 CRUD，不重复计算 |
| 低 | efinance | 少量接口发现/批量模式 | 低到中 | 不恢复累计净值计价，不复制关闭 TLS 校验 |
| 采购验证 | iFinD / Tushare | 前者试查估值缺口；后者可选正式历史补充 | 账号条件决定 | 不按收费标签推定覆盖/准确性 |

MCP 选择：**仅少量只读工具时先比较官方 SDK 的最小实现；需要 FastAPI 转接、组合或 MCP Apps 时 FastMCP 更值得评估。** 两者都不能解决无数据、旧报价或错误字段本身。

### 可以复用的当前代码接点

| 现有位置（仓库根目录相对路径） | 应复用职责 |
|---|---|
| fund-tracker/backend/app/core/data_source.py | 当前提供商、结果模型、单批共享采集/比较路径 |
| fund-tracker/backend/app/core/quote_policy.py | 正式 NAV/平台估值/推算的选择规则 |
| fund-tracker/backend/app/core/history_data.py | 日期、NAV、日收益及比较收益口径 |
| fund-tracker/backend/app/services/fund_service.py | 已有披露持仓、实时/历史/比较/筛选能力 |
| fund-tracker/backend/app/services/portfolio_service.py | 持仓和交易业务；MCP 首期只读 |
| fund-tracker/frontend/src/views/Home/HomeView.vue | 已有来源对比展示；提醒不能另发重复请求 |
| fund-tracker/frontend/src/views/Compare/CompareView.vue | 现有收益比较，后续可增风险/暴露解释 |
| data-source-test/sources/tushare_source.py | 只能作为待校正的测试适配器，非生产接入成果 |

除前述外，估值采样与正式 NAV 日期对齐的误差统计仍很有价值，但这主要是复用本项目已有诊断，不必引入六个项目中的任何整套框架。本次没有创建持续监测或自动化任务。

## 七、证据、版本和限制

源码审查固定版本：

| 项目 | 固定提交 | 根许可证 |
|---|---|---|
| AKShare | fe10d1decb705e5f43cc8ca3339ca39e580fb8f4 | MIT |
| efinance | c8fd370a3109b2d14a121e3a32a86e9c8354b01b | MIT |
| Leek Fund | 425bc79484218064e4ecdb1dea272733befabbd4 | BSD-3-Clause |
| OpenBB | 7c9d4221bdf66965e3f6c7f4dc6ee848073e5ae2 | Apache-2.0（人工核对根 LICENSE，API 元数据为 NOASSERTION） |
| FastMCP | e2fcc412001ff7414095c5dc282f94c70299a612 | Apache-2.0 |
| MCP Python SDK | 754254c08fe1c3eda18b69da3d336106fe8d72d6 | MIT |

“当前源码”不等于生产应安装 develop/main 分支。正式实施需要选发布版本、核对目标文件及依赖许可、保留必要版权/NOTICE、适配现有环境并运行测试。开源代码许可证与金融数据展示/再分发权限分开核对。

本次未用授权账号请求 iFinD/Tushare 业务数据，因此不能提供本项目实际覆盖率、真实延迟、跨日正确率或历史估值误差。公开文档可验证接口与标价，不替代账号权限验收。部分同花顺主站页面访问不稳定，使用同一官方 51ifind 域的文档入口和 GitHub 官方源码 API交叉检查；未将第三方价格帖作为证据。

### 一手来源（访问日期均为 2026-10-14）

- [S1：同花顺权限页](https://ftwc.51ifind.com/gwstatic/static/ds_web/quantapi-web/help-center/permission.html)
- [S2：同花顺 FAQ，账号定义](https://quantapi.51ifind.com/gwstatic/static/ds_web/quantapi-web/help-center/faq.html)
- [S3：同花顺产品手册，登录与基金实时估值](https://ftwc.51ifind.com/gwstatic/static/ds_web/quantapi-web/help-center/manual.html)
- [S4：同花顺 HTTP token 示例](https://quantapi.51ifind.com/gwstatic/static/ds_web/quantapi-web/example.html)
- [S5：Tushare 积分、频次与价格](https://tushare.pro/document/1?doc_id=290)
- [S6：Tushare fund_nav](https://tushare.pro/document/2?doc_id=119)
- [S7：Tushare ETF 实时日线](https://tushare.pro/document/2?doc_id=400)
- [S8：Tushare ETF 实时参考](https://tushare.pro/document/2?doc_id=454)
- [S9：Tushare 积分获得规则](https://tushare.pro/document/1?doc_id=13)
- [S10：Tushare 服务协议](https://tushare.pro/document/1?doc_id=405)
- [S11：AKShare 官方仓库](https://github.com/akfamily/akshare)
- [S12：AKShare 基金披露持仓源码](https://github.com/akfamily/akshare/blob/fe10d1decb705e5f43cc8ca3339ca39e580fb8f4/akshare/fund/fund_portfolio_em.py)
- [S13：AKShare 分红/拆分源码](https://github.com/akfamily/akshare/blob/fe10d1decb705e5f43cc8ca3339ca39e580fb8f4/akshare/fund/fund_fhsp_em.py)
- [S14：efinance 基金源码](https://github.com/Micro-sheep/efinance/blob/c8fd370a3109b2d14a121e3a32a86e9c8354b01b/efinance/fund/getter.py)
- [S15：Leek Fund 官方仓库](https://github.com/LeekHub/leek-fund/tree/425bc79484218064e4ecdb1dea272733befabbd4)
- [S16：FastMCP 官方仓库](https://github.com/PrefectHQ/fastmcp)
- [S17：FastMCP 与 FastAPI 集成](https://gofastmcp.com/integrations/fastapi)
- [S18：FastMCP Apps](https://gofastmcp.com/apps/overview)
- [S19：OpenBB 官方仓库及 Workspace 定位](https://github.com/openbq-org/OpenBB)
- [S20：OpenBB Fetcher 分层源码](https://github.com/openbq-org/OpenBB/blob/7c9d4221bdf66965e3f6c7f4dc6ee848073e5ae2/openbb_platform/core/openbb_core/provider/abstract/fetcher.py)
- [S21：OpenBB OBBject 源码](https://github.com/openbq-org/OpenBB/blob/7c9d4221bdf66965e3f6c7f4dc6ee848073e5ae2/openbb_platform/core/openbb_core/app/model/obbject.py)
- [S22：OpenBB 固定版本 LICENSE](https://github.com/openbq-org/OpenBB/blob/7c9d4221bdf66965e3f6c7f4dc6ee848073e5ae2/LICENSE)
- [S23：MCP Python SDK 官方文档](https://py.sdk.modelcontextprotocol.io/)
