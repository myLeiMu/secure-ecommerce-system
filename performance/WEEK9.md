# 第九周 JMeter 性能基线与优化

本周沿用二手交易平台的三个身份，测试流量来自两个独立交易用户。任务接口为登录、商品查询和下单；购物车是下单前置操作，单列统计。

## 固定实验环境

| 项目 | 前后共同配置 |
| --- | --- |
| 主机 | 本机 Windows，WAF Python，版本/CPU/内存见 environment.json |
| HTTP 服务 | 独立回环 127.0.0.1:8769，Waitress，1 进程 4 线程 |
| 数据库 | MySQL 8.0.43，同一实例，每轮新建随机 test_week9_ 库，InnoDB |
| 数据 | 6 个虚构账号，102 分类，20000 件二手商品，单件库存 1 |
| 用户隔离 | 每个线程一个 perf_user_N 交易账号，全局递增商品号，避免共享购物车 |
| 口令算法 | PBKDF2-HMAC-SM3，2500 次、32 字节；原生实现保持相同结果 |
| 缓存 | Django LocMem，容量 2000；两组都不启用 Redis |
| SQLAlchemy 连接池 | size=10、overflow=20、timeout=30、pre_ping=True，前后容量不变 |
| 负载 | 2 并发，2 秒 ramp-up，每个请求前暂停 1000 ms |
| 采样 | 每轮每线程 2 次预热 + 25 次正式测量，3 轮；每接口每组 150 正式样本 |
| 安全约束 | 原 JWT、权限、审计、每 IP 每分钟 100 次限流保留，无伪造客户端 IP |
| 流程 | login → products（分类 1）→ setup_cart → order |

这是**隔离 MySQL API 实验**，不经过 nginx/TLS，也不代表生产最大并发容量。实验专用 settings 仅关闭这个回环入口的 HTTPS 重定向并固定 LocMem；生产 HTTPS 配置保持不变。JMeter 与数据库和应用在同一主机，资源监控保留整机 CPU，复现时避免并行跑测试/构建或其他压测。

第八周 SQLite/wsgiref 数据不参与本次提升比例计算。旧代码副本来自第八周提交 `3a81987`；新代码副本由 WORKTREE 复制并记录源码 SHA256。两个副本的临时密钥目录独立，旧版每请求生成密钥的行为也不会覆盖真实 keys。

## 文件入口

- [JMeter 测试计划](week9-comparison.jmx)
- [执行器](../scripts/week9_perf.py)、[隔离服务](../scripts/week9_server.py)、[隔离配置](../scripts/week9_settings.py)
- [统计与同环境核验](../scripts/compare_week9.py)
- [优化前原始证据](../docs/evidence/week9/before-final/)
- [优化后原始证据](../docs/evidence/week9/after-verified/)
- [前后对比](../docs/evidence/week9/comparison/summary.md)
- [真实 MySQL 并发正确性](../docs/evidence/week9/concurrency-verified/results.json)

## 复现命令

先激活 WAF，确认 MySQL 可用，根目录 `.env` 为本机连接配置。执行器只读取数据库连接参数，不改密码；数据库账号需要创建/删除**独立测试库**的权限。普通生产应用账号不应为了压测额外开放权限，必要时使用单独的实验环境。不要打印或提交 `.env`。

```powershell
conda activate WAF
python scripts/build_week9_jmx.py
python scripts/week9_perf.py --source-ref 3a81987 --output docs/evidence/week9/before-new --allow-errors
# 前一条完成后再执行，不能并行
python scripts/week9_perf.py --source-ref WORKTREE --output docs/evidence/week9/after-new
python scripts/compare_week9.py --before docs/evidence/week9/before-new --after docs/evidence/week9/after-new --output docs/evidence/week9/comparison-new
```

默认 JMeter 路径为 `D:/apache-jmeter-5.6.3/apache-jmeter-5.6.3/bin/jmeter.bat`，其他机器使用 `--jmeter` 指定。需要 Java、WAF 的 psutil；画图使用 matplotlib。初次检查可增加 `--smoke-only`，输出仍须指定新目录。

旧版本实测有并发错误，`--allow-errors` 仅允许执行器保存完整基线而不提前退出，**不会把失败改成成功**。前后 JMX 都继续采样，断言均要求 HTTP 200、业务 code=0、有效 token/订单 ID；登录失败后 token 提取器返回 MISSING，其后越权失败仍计入错误率。优化后执行器默认不接受任何错误，这比 1% 的验收门槛更严格。

中断后仅在环境、源码摘要和 JMX 一致时可增加 `--resume`；已完成的轮次不重测。部分样本单独归档为 `round-N-interrupted-*`，不混入最终统计。恢复时仅清理本执行器此前新建、无活动连接、账号组成符合固定夹具的随机测试库。

每轮结束验证真实新增订单数等于成功 order 样本数、库存不为负，并清理本进程创建的测试库。成功轮次还要求购物车清空。数据库名、清理结果、失败日志都保留，不用成功报告覆盖历史失败。

## 指标口径

- 并发数：2 个独立线程；每轮 50 个样本/目标接口，三轮合计 150。
- p95：合并三轮正式原始样本，排序取第 `ceil(0.95*n)` 个；包含失败样本，另列各轮 p95。不能平均三个分位数代替总体 p95。
- 错误率：HTTP/业务断言失败数 ÷ 全部正式样本数；429/401/500 都是失败。
- 吞吐量：该接口样本总数 ÷ 各轮该接口活动窗口秒数之和，排除轮次间启动/清理等待；包含流程等待，不是饱和 QPS。
- CPU/RSS：每秒采集后端 Python CPU（单核 100%）、RSS 与整机 CPU，分开记录启动、预热、测量阶段。
- SQL/连接池：记录语句次数、执行耗时、DDL、借出/归还和峰值占用；SQL 计数排除监控 SELECT，连接池计数包含监控连接。
- EXPLAIN：每轮保存相同分类列表查询的 MySQL 执行计划，用来核对复合索引及 filesort。

JTL 不保存请求正文、响应正文或 Authorization。公开的是虚构数据的统计，不是业务数据库快照。临时源码、密钥与详细运行目录位于忽略的 `dist-releases/`。

## 课堂展示

1. 用 JMeter GUI 打开 week9-comparison.jmx，指出两个线程、独立用户名、商品计数器、四个采样器、JWT 提取器和断言。
2. 打开两组 environment.json，核对共同配置、JMX 摘要与代码摘要；说明为什么不用第八周 SQLite 数值作分母。
3. 打开 comparison/summary.md 和 comparison.png，讲清三接口 p95、吞吐量、错误率；展示一个 JTL 原始失败样本及最终成功样本，证明错误没有被删掉。
4. 对照 query-plan.json、SQL 计数和 CPU/RSS，说明性能改善的机制与边界。
5. 展示 concurrency-verified/results.json：同时抢一件商品只有一单成功、库存为零、缓存刷新且越权被拒绝；展示五轮首次并发登录成功和已有 MFA/安全版本保持的记录。
6. 如需现场重测，运行一个独立 `--smoke-only` 实验，不对生产账号/真实二手商品点击 Start 压测。JMX 自身不会创建测试数据库，不能单独对生产 8443 修改地址后运行。

参考：[JMeter 非 GUI 模式](https://jmeter.apache.org/usermanual/get-started.html#non_gui)、[Python hashlib](https://docs.python.org/3.13/library/hashlib.html)、[SQLAlchemy 会话和连接归还](https://docs.sqlalchemy.org/en/20/errors.html#queuepool-limit-of-size-x-overflow-y-reached-connection-timed-out-timeout-z)。
