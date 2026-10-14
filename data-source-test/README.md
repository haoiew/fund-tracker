# 数据源核查与旧基准工具

当前生产数据源核查入口为 `check_availability.py`，复用主应用适配器，检查有效数据、源端估值、真实时刻、逐源响应和历史口径，不写持仓/历史数据库。

**最新实时估值专项核查为 `check_estimate_coverage.py`**：并排保存天天原始空字段与新浪真实估值，依据新浪自身脚本验证字段映射；可选 `--api-base` 验证实际前端代理的加载耗时。该核查器保留两源同刻对照，不能代替当前四源渐进采集验收；应用现全源并发并优先新浪，天天仅使用 POST。

**稳定性、速度及新候选评估用 `evaluate_realtime_sources.py`**：同批六基金比较天天 GET/POST、新浪、Dayfund、Fund123，统计请求/业务成功、估值覆盖、整批延迟 P50/P95、实际报价年龄与时刻推进。用户已批准两候选接入生产；GET/POST 仅作为同服务的诊断对照，不重复注册生产源；Fund123 通过正常匿名页面流程取数，不保存 CSRF/Cookie。

```powershell
# 在仓库根目录，使用已有非 base 命名环境
conda activate fund-tracker
python -B .\data-source-test\check_availability.py --rounds 2 --interval-seconds 10
# 实时估值覆盖、字段映射与已运行应用的真实加载
python -B .\data-source-test\check_estimate_coverage.py --rounds 2 --interval-seconds 15 --api-base http://127.0.0.1:3000/api
# 直接访问免费来源的同条件比较，不经过应用报价缓存
python -u -B .\data-source-test\evaluate_realtime_sources.py --rounds 10 --interval-seconds 15
# 新评估器的离线解析/统计回归，不调用网络
python -B -m pytest .\data-source-test\tests\test_realtime_benchmark.py -q
```

可通过 `--codes` 指定逗号分隔的六位代码、`--output` 指定 JSON 输出；可调整设置集中在脚本顶部。查询日期不是净值日期，HTTP 200 不等于业务数据可用，有效净值也不等于实时估值。

`run_all_tests.py` 和 `sources/` 保留为旧库级探索工具，**不是当前生产选择逻辑**：旧东方财富适配器仍探测已失效的 fundgz，efinance 原路径混入累计净值，AKShare 还可能返回 LOF 成交价。旧报告的成功率/价格一致性不能证明实时估值覆盖或单位净值准确性；不要据其分数恢复生产数据源。统一其结果口径属于后续重构项，本次新核查器作为当前证据入口。

2026-10-13 的样本与完整说明见 [核查报告](../fund-tracker/docs/DATA_SOURCE_AND_AGENT_PLAN_20261013.md)及 [原始证据](reports/availability_20261013.json)。授权源、凭证不完整的服务不计为已实测可用。本次没有安装额外依赖。

最新 2026-10-14 盘中复核、指数查询及真实 API 联调见 [最新证据](reports/availability_20261014.json)，与前一日记录分开保存，避免将旧估值当作今日实时数据。

新浪接入后的 14:33 两轮 30 样本、真实 3000 代理的 23 代码与 18 条持仓覆盖见[估值专项证据](reports/estimate_coverage_20261014.json)和[解释报告](../fund-tracker/docs/ESTIMATE_FALLBACK_20261014.md)。本次接口成功率不能推定估值准确度或再分发授权，报价阶段耗时不含浏览器绘制。

14:58–15:18 的[稳定性/速度/新增备用源评估](../fund-tracker/docs/FREE_REALTIME_SOURCE_BENCHMARK_20261014.md)另记录了天天的陈旧窗口及恢复、Dayfund/Fund123 的实际覆盖限制和本机代理条件，不能用早期两轮成功替代长期稳定性证据。原始记录：[广样本30轮](reports/stability_samples_20261014.json)、[同条件比较](reports/realtime_benchmark_20261014.json)、[其他公开路径](reports/other_free_candidates_20261014.json)。
