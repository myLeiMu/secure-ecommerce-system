# 第九周更高并发补充实验

2026-10-28。新增 10、30 并发的 LocMem / WSL Redis 对照，保留此前所有结果；不提交 Git，不改变正式业务配置。

## 报告入口

- [两档并发汇总](../evidence/week9/concurrency-20261028/summary.md)、[JSON](../evidence/week9/concurrency-20261028/summary.json)
- [10 并发对比](../evidence/week9/concurrency-20261028/comparison-10/summary.md)、[图](../evidence/week9/concurrency-20261028/comparison-10/comparison.png)
- [30 并发对比](../evidence/week9/concurrency-20261028/comparison-30/summary.md)、[图](../evidence/week9/concurrency-20261028/comparison-30/comparison.png)
- [原有限流边界实测](../evidence/week9/concurrency-20261028/guard-10/round-1/measurement.jtl)

## 实测结论

四组均完成三轮且错误率为 0%。10 并发时，商品查询 p95 为 LocMem 133 ms、Redis 131 ms，登录/下单则 LocMem 略低。30 并发时，登录、查询、下单 p95 分别为 LocMem 523/423/521 ms、Redis 651/504/628 ms，三个接口均为 LocMem 较低。

10 → 30 并发，LocMem 下单流程吞吐从 22.94 到 24.00 req/s，Redis 从 22.38 到 20.94 req/s，响应延迟却明显增加。本实验没有发现“提高并发后 Redis 明显更快”。结果符合处理能力受限、更多请求等待的表现，但没有逐段剖析证明具体瓶颈。单进程、4 工作线程、频繁商品失效及跨 WSL 通信都是解释结果时需要保留的条件。

两种缓存各档位只做三轮短时测量，实例与其他项目共用，不能把差值当作普遍结论；未测多进程或读多写少场景。

## 为什么分开测限流和容量

正式中间件限制每个 IP 每分钟 100 次请求，商品查询免限流。单台 JMeter 全部请求来自同一 IP，高并发会先触发安全限制。

先保留该配置，运行 10 用户、每用户 5 次正式循环（预热另存）。登录 50 次中有 35 次 429，商品查询 50 次全部成功。登录失败后 token 为 MISSING，后续购物车和下单产生 401；下单另有 5 次 429。这些错误完整保留，不通过伪造来源 IP 或删除失败记录掩盖。

然后在**隔离回环测试 settings** 中启用显式 `--capacity`，仅移除该 IP 限流中间件。必须使用随机 `test_week9_` 数据库，服务只监听 127.0.0.1；认证、审计、权限、密码成本、订单事务与库存锁保留。正式 `service/settings.py` 没有变化。

因此容量结果表示“临时排除入口 IP 限流后的内部 API 处理能力”，不能说是正式入口保持原安全策略下能提供的吞吐量；也不能替代原第九周同环境优化验收。

## 固定条件

| 项目 | 设置 |
| --- | --- |
| 并发等级 | 10、30；每个 JMeter 线程一个独立交易账号 |
| 后端 | Waitress 单进程、4 工作线程，未随负载扩容 |
| 连接池 | size=10，overflow=20，容量保持不变 |
| 商品 | 每轮 20000 件，单库存；全局计数器避免线程购买同一件商品 |
| 采样 | 每组 3 轮，每线程预热 2 次、正式 20 次；分别 600、1800 样本/目标接口/组 |
| 升压与等待 | 2 秒升压、请求间不加入思考等待 |
| 流程 | 登录 → 查询分类商品 → 加购物车 → 下单 |
| 后端顺序 | 10 并发先 LocMem 后 Redis；30 并发先 Redis 后 LocMem，全程串行 |
| Redis | 原 WSL 实例，每轮随机键前缀，仅删除本轮键，不 FLUSHDB |

两种缓存在同一并发级别核对相同源码摘要、依赖、JMX、MySQL 与非缓存配置。各轮重建相同商品夹具、清理测试库及 Redis 键；保留 SQL、连接池、CPU/RSS、缓存命中和订单落库检查。

原 2 并发实验有每请求 1 秒等待，本实验去掉等待，故不能把 2 与 10/30 的吞吐差直接归因于“只增加了并发”。可直接比较的是本次同一档位的 LocMem 与 Redis，以及同一无等待负载下的 10 与 30。

## 复现

```powershell
conda activate WAF
# 保留正式限流，所有失败必须记录；输出目录使用新名称
python scripts/week9_perf.py --source-ref WORKTREE --threads 10 --pause-ms 0 --loops 5 --repeats 1 --allow-errors --output docs/evidence/week9/concurrency-new/guard-10
# 两档、两种缓存，各三轮；不与其他压测或构建并行
python scripts/week9_concurrency.py --output docs/evidence/week9/concurrency-new
```

`--allow-errors` 只允许完整采样，所有失败仍计入错误率；落库订单数不一致、负库存、缓存异常仍会阻止有效结果。是否满足 1% 错误率必须查看实际统计，不能用进程退出码代替。

单组中断后可以使用相同参数运行 `week9_perf.py --resume`，只保留完整轮次；批量执行器要求新的输出目录，不自动覆盖历史实验。

这是固定循环的短时并发敏感性实验，没有验证多进程共享缓存、长时间稳定性或 nginx 8443 的 TLS/mTLS 开销。后端只有 4 个工作线程，增加客户端并发会使请求排队；Redis 不会自动增加 SQL 或后端处理能力。每次下单还会旋转商品缓存版本，需结合命中率解释结果。
