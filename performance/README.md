# 第 8 周：性能基线准备

任务书接口为 **登录、商品查询、下单**。本周完成脚本、联通、冒烟和小样本基线；第 9 周才做优化及同环境对比。

## 运行

在项目根目录的 PowerShell：

```powershell
conda activate WAF
python -m pip install -r docs/requirements/security-tools.txt
python scripts/week8_perf.py --output docs/evidence/week8/performance-new-run
```

`--output` 必须是不存在的目录，防止覆盖旧证据。需要 Java 与 Apache JMeter 在 PATH；本机是 Java 21、JMeter 5.6.3。也可以传 `--jmeter D:/apache-jmeter-5.6.3/apache-jmeter-5.6.3/bin/jmeter.bat`。启动前确认 8768 空闲。退出时临时数据销毁，不需要启动真实 8080 后端。

在 JMeter GUI 中打开 `performance/week8-baseline.jmx` 可以查看线程组、请求、令牌提取与断言。实际测量使用非 GUI 模式，脚本会自动启动临时 API 并调用 JMeter。

## 当前固定口径

| 项目 | 固定设置 |
| --- | --- |
| 入口 | HTTP 127.0.0.1:8768，只监听回环 |
| 服务 | WAF Python、真实 Django API/中间件；wsgiref 单进程、单请求处理 |
| 数据库 | 隔离 SQLite 共享内存库，每轮重置；不是实际 MySQL |
| 缓存 | 本地内存缓存，测试设置禁用 Redis |
| 数据 | 5 个虚构账户、1000 件二手商品，每件库存 1；历史 merchant fixture 转成 normal |
| 身份 | 交易用户可买可卖，另有管理员、审计员；没有增加第四种业务身份 |
| 认证 | 真正登录与 JWT 校验，SM3-PBKDF2 2500 轮；没有采用单测的 50 轮捷径 |
| 安全 | 保留权限、审计、100 次/IP/60 秒限流；商品查询仍按现有代码豁免 |
| 负载 | 1 个并发用户，启动 1 秒，每个请求前等待 1000ms |
| 流程 | login → products → setup_cart → order；每次购买不同商品 |
| 冒烟 | 1 次流程；三个目标接口加一次购物车前置操作 |
| 基线 | 3 轮，每轮 2 次预热、10 次测量；预热另存，不混入指标 |

测试夹具仅替换数据库初始化、初始数据与密钥生成，随后调用真实业务视图。数据库中有真实插入的测试订单；每轮额外校验订单数量及购物车清空。认证、商品查询、下单逻辑没有替换为假响应。

`setup_cart` 是下单必要的准备操作，单独统计，不冒充第四个任务接口。JMeter 对 HTTP 200、JSON `code=0`、登录令牌及订单 ID 做断言；错误会停止当前线程，并让执行器失败。JTL 不记录请求/响应正文、Authorization 或 token。

## 指标和证据

- `environment.json`：Python/Java/JMeter/Node/依赖版本、CPU/内存、代码文件 SHA256、数据库/缓存/安全参数。
- `smoke.jtl`：冒烟真实采样记录。
- `baseline-N.jtl`：各轮测量原始记录；`baseline-N-warmup.jtl` 为预热。
- `results.json`：样本数、错误率、p95、平均响应时间、吞吐量及订单落库验证。
- `baseline-N-resources.json`：每秒后端进程 CPU（单核 100%）、RSS，区分预热和测量阶段。
- `*-console.txt`：JMeter 非 GUI 执行记录。原始 `.log` 被仓库忽略，保留在本机排障。

p95 采用 nearest-rank：排序后取第 `ceil(0.95*n)` 个样本，包含错误请求；错误率是失败样本/全部样本。单接口吞吐量是该接口样本数除以“最后一个结束时刻－第一个开始时刻”，包含业务流程与等待时间，因此不是最大 QPS。10 个样本时 p95 等于最大值，**本周的小样本不能用来证明容量或 20% 优化效果**。

## 第 9 周如何接续

1. 如继续用这个隔离环境做教学对比，保持数据量、版本、代码之外的环境参数、认证成本、安全策略和负载一致，并扩大持续时间和样本数。先提高负载测出可解释的基线，再做优化。
2. 如选择真实 `nginx 8443 → Django → MySQL/Redis`，必须先建立独立的压测库和压测账号，冻结 worker/连接池/Redis/HTTPS 配置并重测基线。不能把本周 SQLite 的数值直接当成 MySQL 的优化前数据。
3. 当前 JMX 固定一个交易用户。多用户并发前需用 CSV 为每个线程分配独立交易账号和商品，避免共享购物车、重复购买单件商品、库存竞争污染结果。保留防护；429 单独报告，不能算成功，也不能通过静默关闭限流制造达标结果。
4. 优化目标遵循任务书：同环境 p95 下降至少 20%，或给出已达标保持证明，错误率不高于 1%。第 8 周不声称完成这部分。

参考：[JMeter 非 GUI 模式](https://jmeter.apache.org/usermanual/get-started.html#non_gui)、[生成 HTML Dashboard](https://jmeter.apache.org/usermanual/generating-dashboard.html)。
