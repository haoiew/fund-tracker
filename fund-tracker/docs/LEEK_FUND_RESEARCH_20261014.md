# LeekFund 场外基金功能、数据源及免费 / Pro 边界核查

> 核查日期：2026-10-14（Asia/Shanghai）。指定提交：`425bc79484218064e4ecdb1dea272733befabbd4`。证据来自固定提交源码、项目官网文档、维护者在项目 Issues 中的回复，以及 Microsoft Marketplace 当前公开发布包。本文是只读研究，不是采购、安装或代码移植授权。

## 一、结论先看

1. **它是编辑器里的行情展示及本地持仓管理工具，不是自建基金估值数据供应商。** 所查估值主链路读取天天基金 / 东方财富提供的净值、估值及时间字段；Pro 没有被官方描述为另一套独家或全市场覆盖的基金实时数据服务。[S4][S14][S16][S25]
2. **场外基金功能不止盘中估值。** 固定源码实现了历史净值和走势图、回报排行、基金资料、阶段收益、机构评级、源端盈利概率指标、基金披露持仓、手动持仓金额及简易盈亏等；当前 Pro 再增加分组与完整资产管理。[S5][S6][S7][S8][S9][S11][S12][S13]
3. **不限定 VS Code 本体，但仍依赖 VS Code 兼容编辑器。** 官方列出 VS Code、Cursor、Trae、Qoder、Insiders；本次未发现官方独立 Windows/macOS/Linux 桌面客户端。官网是介绍、文档和账号/授权入口，不应当成独立基金分析终端。[S1][S15][S26]
4. **不是所有功能都免费。** 当前产品是免费基础功能加付费 Pro。开源许可证、免费基础版、付费产品权限是三个不同层面。[S3][S11][S13]
5. **购买 Pro 不等于解决缺失的基金估值。** 2026-07-21 的旧接口故障、随后主动基金估值缺失讨论，说明限制来自上游覆盖；维护者也指出披露持仓滞后会使自行推算有偏差。[S19][S20]
6. **当前价格不可据旧网页确定。** 2026-10-14 定价入口跳转维护页；维护者在 2026-10-10 提到服务器费用压力、关闭公开入口，并让有需要者走闲鱼订阅。没有核实到现行准确金额、期限及设备额度，不沿用历史报价。[S21][S22]

## 二、必须先分清的版本

| 对象 | 核实结果 | 研究边界 |
|---|---|---|
| 用户指定提交的源码 | 根 `package.json` 为 **3.24.0**；旧 `CHANGELOG.md` 的 3.24.0 记录为 2026-04-23 | 是可以逐文件核查的旧实现，不是完整当前 4.x Pro 源码。[S1] |
| 同一提交的 README | 已经介绍 4.x 的免费 / Pro 产品功能 | 宣传文档比该目录中的实现新，不能用 README 证明全部 Pro 功能已在此提交中实现。[S2] |
| 官网更新日志 | 最后列出的条目为 2026-08-09 的 **4.3.3** | 官网日志不等于市场当前最新版；本次另核实发布元数据。[S18] |
| Marketplace 当前发布包 | **4.3.4**，发布元数据更新时间为 **2026-08-13**；清单与包内 `package.json` 均为 4.3.4 | 本次只下载并静态读取公开 VSIX，未安装或运行扩展，也未绕过订阅限制。[S23][S24][S25] |

固定源码还直接注册了基金分组命令，而现行文档把自定义基金分组列为 Pro。因此，“旧版开源功能”和“现行免费版权限”也不能混为一谈。[S10][S12]

### 发布包核查记录

- 来源：Microsoft Marketplace 官方 gallery 资产，版本固定为 4.3.4。[S24][S25]
- 包大小：9,337,958 字节。
- SHA-256：`EC3A038D0DC1EDCBCF0DE6B8FF216C453309C69FA7EDE08E0150D17CB63322B9`。
- 静态读取：`extension/package.json`、`extension/out/explorer/fundService.js`、`extension/out/shared/marketDataConfig.js` 等。
- 发布 JS 存在混淆；基金接口结论来自字符串表静态解码、轮转算式核对和字段映射阅读。**没有执行扩展代码、没有调用或修改 Pro 权限逻辑。**
- 4.3.4 清单中的许可证仍标为 BSD-3-Clause；这不意味着仅下载用户给出的旧源码就能还原全部现行产品。[S24]

## 三、场外基金相关功能

### 先把概念区分开

- **单位净值（NAV，元/份）**：每份基金份额对应的基金公司正式披露净值，必须带净值所属日期；它不等于盘中估值。[S4][S19]
- **盘中估值（GSZ，元/份）**：上游提供的盘中估算单位净值；`GSZZL` 是估算涨跌幅（%），`GZTIME` 是估值时刻。它不是交易成交价，也不是当日正式净值。[S4][S19]
- **基金披露持仓**：基金在披露截止日持有的股票及其权重，是基金经理管理的投资组合；不等于用户自己购买的基金份额，也不代表今天的完整实时持仓。[S7][S8][S20]
- **我的持仓 / 账本**：用户在本机录入的基金数量、金额、成本及加仓等记录，用于计算用户盈亏；不是自动读取支付宝、券商或基金销售平台账户。[S13][S14]

| 功能 | 所查实现与具体内容 | 适用边界 |
|---|---|---|
| 基金自选 | 搜索代码、添加 / 删除 / 置顶，查看列表，按涨跌或持仓金额排序 | 指定源码通过编辑器命令与配置保存；现行免费版仍有简单自选列表。[S1][S10][S12] |
| 估值及净值概览 | 显示估算净值、估算涨跌、正式净值日期及估值时间；侧栏 / 状态栏展示 | 依赖上游返回，不等于自建估值算法；海外 / QDII 宣传支持不代表每只都有盘中估值。[S4][S12][S19] |
| 实时 / 历史走势图 | 单只基金图、基金走势一览、单位净值走势、累计收益率走势 | 指定源码加载东方财富脚本、图像及 `Data_netWorthTrend` / `Data_grandTotal`，不是任意多基金统一收益口径的比较引擎。[S5] |
| 历史净值明细 | 日期、净值及涨跌等历史表格，并链接更多历史数据 | 指定源码单次请求 `per=49`；不是完整本地历史数据库。[S6] |
| 排行和同类参考 | 回报排行、不同期限收益、同类基金列表 | 旧 / 新排行默认均取前 40；不是连涨连跌、最大回撤等复杂筛选器。[S4][S8][S25] |
| 基金基本资料 | 类型、成立日期、经理、规模、综合评级 | 固定源码抓取天天基金页面 HTML，随页面结构变化存在失效风险。[S8][S9] |
| 阶段收益 | 近 1、3、6 个月、1 年、3 年及成立以来收益 | 来源于上游网页，不是用户自己的持有收益率。[S8] |
| 机构评级 | 招商、济安金信、上海证券评级及评级日期 | 第三方评级展示，非 LeekFund 自建评级模型。[S8][S9] |
| 源端盈利概率指标 | 持有 7 天、3 个月、6 个月、1 年的盈利概率及评分 | 固定源码直接展示东方财富诊断接口字段；本次未验证统计口径和当前可用性，不能当作未来收益保证。[S8][S9] |
| 披露持仓 | 前十重仓股、权重、披露截止日、持仓明细图；某些视图显示这些股票的当前涨跌 | 只是历史披露的仓位加上当前股票行情，不等于基金当天完整实时仓位。[S7][S8][S9][S20] |
| 简易持仓盈亏 | 用户设置基金持仓金额 / 成本，列表与状态栏显示盈亏 | 免费版仍保留简单维护入口；金额口径与账本完整度有限，不能等同真实平台结算账单。[S4][S12][S14] |
| 完整资产管理 | 统一股票 / 基金账本、成本与数量、总资产、浮动盈亏、编辑 / 加仓 / 删除、JSON 导入导出 | 现行 Pro 功能；“加仓”是在本地记账，不执行真实基金申购。[S11][S13][S14] |

没有找到可据以承诺的自动申购 / 赎回、真实基金账户同步、完整交易结算或全市场主动基金估值覆盖。更准确的定位是“看行情、查资料、维护本地持仓”，不是基金销售或专业投研终端。[S14][S15][S19][S20]

## 四、它到底使用什么数据源

### 可复核的接口与版本差异

| 功能 / 版本 | 上游 | 所查接口 / 实现 |
|---|---|---|
| 指定源码 3.24.0 的基金估值 | 天天基金 / 东方财富 | `https://fundgz.1234567.com.cn/js/{code}.js`，解析 `jsonpgz(...)`；逐基金请求后 `Promise.allSettled` 汇总。[S4] |
| 当前发布包 4.3.4 的估值主接口 | 天天基金 / 东方财富 | `https://fundcomapi.tiantianfunds.com/mm/newCore/FundValuationLast`。[S24][S25] |
| 当前发布包 4.3.4 的估值备用接口 | 同一东方财富上游的备用域名 | `https://fundcomapi.eastmoney.com/mm/newCore/FundValuationLast`；不是新的独立数据供应商。[S19][S25] |
| 指定源码 3.24.0 的排行榜 | 新浪财经 | `vip.stock.finance.sina.com.cn/fund_center/data/jsonp.php`，`NetValueReturn_Service.NetValueReturnOpen`；按今年以来收益取前 40。[S4] |
| 当前发布包 4.3.4 的排行榜 | 东方财富 | `https://fund.eastmoney.com/data/rankhandler.aspx`，`op=ph&dt=kf&ft=all&sc=jnzf&st=desc&pi=1&pn=40` 等参数。[S25] |
| 指定源码的净值历史 | 天天基金 / 东方财富 | `fund.eastmoney.com/f10/F10DataApi.aspx?type=lsjz&code=...`。[S6] |
| 指定源码的图表 | 东方财富 | `fund.eastmoney.com/pingzhongdata/{code}.js`、`j3/j4/j6.dfcfw.com` 图像及脚本。[S5][S7] |
| 指定源码的资料、阶段收益、同类参考 | 天天基金 / 东方财富 | `https://fund.eastmoney.com/{code}.html` 的 HTML 解析。[S8] |
| 指定源码的评级 | 东方财富 | `http://api.fund.eastmoney.com/F10/JJPJ/`。[S8] |
| 指定源码的盈利概率诊断 | 东方财富移动端接口 | `https://fundmobapi.eastmoney.com/FundMNewApi/FundMNCSDiag`。[S8] |
| 指定源码的披露持仓 / 持仓股行情 | 东方财富 | `fundf10.eastmoney.com/FundArchivesDatas.aspx?type=jjcc`、`push2.eastmoney.com/api/qt/ulist.np/get`。[S7] |

4.3.4 估值请求字段为 `FCODE,SHORTNAME,GSZZL,GZTIME,GSZ,NAV,PDATE`，使用 `FCODES` 批量查询；字段映射将估值缺失标为 `noValuation`。所查主链路没有建立自己的基金实时全持仓估值模型。[S19][S25]

**这里的关键不是接口数量，而是上游独立性与实际覆盖。** 天天基金、东方财富及两个 fundcomapi 域名并不是三个独立估值供应商；旧版新浪的这条调用是回报排行，也不能据此说旧版具备“新浪基金实时估值兜底”。[S4][S19][S25]

### 估值可用性的时间线

- **2026-07-21**：Issue #677 报告旧 `fundgz` 对多个基金返回重定向 / 错误页，建议改用 H5 的 `FundValuationLast`。其样本中部分基金有估值，另一些主动基金 `GSZ/GSZZL/GZTIME` 为 null。这是当时的样本，不是本次全市场实测。[S19]
- **2026-07-21**：维护者称 4.3.1 已修复；官网同日也记录修复基金接口，但明确部分基金仍取不到数据。[S18][S19]
- **2026-07-22**：维护者在同一 issue 又指出基金实时估值仍暂不可用；#679 中进一步讨论主动基金缺失和披露持仓滞后的推算偏差。因此不能把“修复接口”解释成“恢复全部主动基金估值”。其政策归因是维护者表述，本次没有独立核查监管政策。[S19][S20]
- **2026-10-14 本次静态核查**：Marketplace 4.3.4 的代码已是新接口，但没有运行扩展或开展今天的基金覆盖测试，不能保证任意基金今天可用。[S25]

默认约 5 秒轮询、最小 3 秒，是扩展请求频率，不是上游净值更新频率、行情延迟或精度保证。Pro 中继文档明确它是透明透传，不改变行情语义；购买中继权限不能让上游恢复没有提供的估值。[S15][S16]

## 五、标准版和 Pro 的区别

“标准版”在本报告中指当前官方文档的免费版，不指固定提交中功能更多的旧版源码。[S11][S12]

| 维度 | 当前免费基础版 | 当前 Pro |
|---|---|---|
| 基金自选与行情 | 基础列表、估值 / 净值 / 涨跌展示 | 基础功能继续具备；没有官方承诺独家高精度或全覆盖基金估值源。[S11][S12][S14] |
| 走势图、历史、排行、资料 | 基础入口及只读工具 | 保留；主要不是 Pro 的核心付费差异。[S2][S11][S12] |
| 持仓维护 | 简单设置持仓金额 / 成本，资产中心只读列表 | 完整账本编辑、加仓、删除、总资产、浮动盈亏、JSON 导入导出。[S12][S13] |
| 自定义分组 | 简单列表 | 多组、重命名 / 删除、跨组移动、拖拽、折叠展开、自动“我的持仓”。[S12] |
| 个性化体验 | 基本设置 | 可视化高级定制、自选快速定位等。[S11] |
| 行情中继 | 可填写并保存配置，但不真正生效 | 自建 Docker / Nginx 透明代理可生效；本机 / NAS / VPS 的运行或托管资源需自行具备。[S16] |
| AI 信息整理 | 不属于免费完整能力 | LeekAgent，整理公开信息；某些宿主建议 BYOK，不能默认理解为 Pro 包含无限免费模型调用。[S15][S17] |
| 综合股票 / 市场工具 | 基础功能 | 快讯、板块行情、大盘云图、Blame 伪装、企业微信 / 钉钉 / 飞书股价预警推送等。[S11] |

官方把 Webhook 描述为股价 / 价格预警，把 Blame 伪装描述为股票行情。它们不能不加区分地算成“场外基金专属 Pro 功能”。[S2][S11]

## 六、为什么要区分，收费是否因为买了更好的数据

### 已证实的产品事实

- 官网记录 **2026-06-01 发布 4.0.0 Pro**，把分组、完整持仓管理、快讯、个性化等能力列为付费增量。[S18]
- Pro 登录用于验证订阅与设备会话；官方说自选、持仓和分组仍保存在本地，并不因为付费而获得平台持仓云同步。[S14]
- **2026-10-10**，维护者在 #685 直接提到服务器费用压力，称未开放注册、关闭公开入口，需要者走闲鱼订阅。这个成本原因有一手证据，不只是推测。[S21]
- 本次定价页显示升级维护；文档仍说月付 / 年付，但没有可核实的现行金额及完整购买方案。不能据此承诺目前一定可以买到某个期限或价格。[S11][S22]

### 解释与推断

**更符合证据的解释是免费基础功能加付费管理 / 工作流能力的产品分层。** 分组、导入导出、高级 UI、自建中继接入等收费，属于功能和授权安排，不是这些功能天然需要另一套付费行情数据。服务器运营成本有维护者证据；持续开发、支持和维护也是合理成本推断，但本次没有财务资料，不量化其占比。[S11][S16][S21]

指定代码的 BSD-3-Clause 允许在遵守声明等条件下使用和修改该份代码；它不是“所有未来新增功能与线上授权服务永久免费”的承诺。当前 Pro 与免费边界要看当前产品文档，完整当前产品能否自行重建还取决于所获代码和对应服务，不能仅凭旧仓库 README 推定。[S1][S2][S3][S11]

**没有证据支持“Pro 收费是为了购买独家、更准、更完整的场外基金估值数据”。** 官方声明原始行情来自第三方公开接口且不担保完整性 / 及时性，Pro 中继也只是透传同一上游。[S14][S16]

## 七、对本项目的实际意义

这是工程判断，不是实施批准：如果目标是改善 Fund Tracker 的场外基金实时覆盖，LeekFund 不构成已验证的独立新数据源。它值得参考的主要是基金资料与披露持仓的组织方式、紧凑列表、分组、资产账本和交互设计；不应直接移植旧 `fundgz` 主链路，也不能将 Pro 宣传功能视为指定源码已经全部具备。[S1][S2][S4][S8][S9][S19][S25]

本次未注册 / 登录 / 购买、未安装扩展、未调用付费模型、未改动现有应用代码、未运行基金数据覆盖基准。研究结论保存在本报告。下载的源码摘取及 VSIX 暂存于 `D:\workdir\code\Explore\work\leek-fund-research-20261014`；已校验该目录属于本次工作区且不是链接，但清理命令被运行策略拦截，材料尚未删除，不属于应用运行依赖。

## 一手来源

所有链接核查于 2026-10-14；源码链接固定到指定 SHA。源码路径和发布包内路径指上游项目，不是本项目新增实现。

- [S1] [指定提交 package.json](https://github.com/LeekHub/leek-fund/blob/425bc79484218064e4ecdb1dea272733befabbd4/package.json)；[旧版 CHANGELOG](https://github.com/LeekHub/leek-fund/blob/425bc79484218064e4ecdb1dea272733befabbd4/CHANGELOG.md)。
- [S2] [指定提交 README](https://github.com/LeekHub/leek-fund/blob/425bc79484218064e4ecdb1dea272733befabbd4/README.md)。
- [S3] [指定提交 LICENSE](https://github.com/LeekHub/leek-fund/blob/425bc79484218064e4ecdb1dea272733befabbd4/LICENSE)。
- [S4] [基金服务 fundService.ts](https://github.com/LeekHub/leek-fund/blob/425bc79484218064e4ecdb1dea272733befabbd4/src/explorer/fundService.ts)。
- [S5] [基金走势 fundTrend.ts](https://github.com/LeekHub/leek-fund/blob/425bc79484218064e4ecdb1dea272733befabbd4/src/webview/fundTrend.ts)；[基金走势一览](https://github.com/LeekHub/leek-fund/blob/425bc79484218064e4ecdb1dea272733befabbd4/src/webview/allFundTrend.ts)。
- [S6] [历史净值 fundHistory.ts](https://github.com/LeekHub/leek-fund/blob/425bc79484218064e4ecdb1dea272733befabbd4/src/webview/fundHistory.ts)。
- [S7] [披露持仓 fundPosition.ts](https://github.com/LeekHub/leek-fund/blob/425bc79484218064e4ecdb1dea272733befabbd4/src/webview/fundPosition.ts)。
- [S8] [基金详情数据请求 services.ts](https://github.com/LeekHub/leek-fund/blob/425bc79484218064e4ecdb1dea272733befabbd4/template-packages/leek-center/src/components/fund-info-panel/services.ts)。
- [S9] [基金详情 UI](https://github.com/LeekHub/leek-fund/blob/425bc79484218064e4ecdb1dea272733befabbd4/template-packages/leek-center/src/components/fund-info-panel/index.tsx)。
- [S10] [编辑器命令 registerCommand.ts](https://github.com/LeekHub/leek-fund/blob/425bc79484218064e4ecdb1dea272733befabbd4/src/registerCommand.ts)。
- [S11] [官网 Pro 功能](https://leek.fund/docs/pro)。
- [S12] [官网基金管理](https://leek.fund/docs/fund)。
- [S13] [官网资产管理](https://leek.fund/docs/holdings)。
- [S14] [官网数据与安全](https://leek.fund/docs/data-security)。
- [S15] [官网快速开始](https://leek.fund/docs/getting-started)。
- [S16] [官网行情中继](https://leek.fund/docs/market-data-relay)。
- [S17] [官网 LeekAgent](https://leek.fund/docs/leek-agent)。
- [S18] [官网更新日志](https://leek.fund/changelog)。
- [S19] [Issue #677：fundgz 故障、新接口与维护者回复](https://github.com/LeekHub/leek-fund/issues/677)。
- [S20] [Issue #679：部分基金估值缺失与披露持仓偏差](https://github.com/LeekHub/leek-fund/issues/679)。
- [S21] [Issue #685：购买入口与维护者 2026-10-10 的成本说明](https://github.com/LeekHub/leek-fund/issues/685)。
- [S22] [官网价格入口](https://leek.fund/pricing)，本次跳转 [维护页](https://leek.fund/pricing/unavailable)。
- [S23] [Microsoft Marketplace 官方插件页](https://marketplace.visualstudio.com/items?itemName=giscafer.leek-fund)。当前版本另以 Gallery `extensionquery` 官方发布 API 核对（筛选 `giscafer.leek-fund`，返回 4.3.4）。
- [S24] [4.3.4 官方清单](https://giscafer.gallerycdn.vsassets.io/extensions/giscafer/leek-fund/4.3.4/1786630200666/Microsoft.VisualStudio.Code.Manifest)。
- [S25] [4.3.4 官方 VSIX 资产](https://giscafer.gallerycdn.vsassets.io/extensions/giscafer/leek-fund/4.3.4/1786630200666/Microsoft.VisualStudio.Services.VSIXPackage)。基金来源结论来自包内 `extension/out/explorer/fundService.js` 与 `extension/out/shared/marketDataConfig.js` 的只读静态核查。
- [S26] [韭菜中心请求桥 fetch.ts](https://github.com/LeekHub/leek-fund/blob/425bc79484218064e4ecdb1dea272733befabbd4/template-packages/leek-center/src/utils/fetch.ts)。其请求通过 `postMessage('fetch', ...)` 交由扩展处理，不能把 React 前端目录误认成已经可独立使用的桌面产品。