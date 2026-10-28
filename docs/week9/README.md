# 第九周：性能基线与优化交付

日期：2026-10-23；平台：二手交易；身份：交易用户、管理员、审计员。第九周范围为性能基线、优化、监控及前后对比，不替代第八周尚待协调的共享数据库密码轮换和 Burp 范围补证。

## 验收入口

- [10 / 30 并发补充实验](HIGH_CONCURRENCY.md)：原有限流边界与独立容量对照分别报告。
- **[2026-10-28 Redis 补充实验](REDIS.md)**：相同优化后代码，新增 LocMem / WSL Redis 实测、命中率和独立缓存清理证据；原验收结果保留。
- **[实测前后对比](../evidence/week9/comparison/summary.md)**：三接口并发、p95、吞吐量、错误率与 CPU/RSS。
- [机器可读结果](../evidence/week9/comparison/comparison.json)、[对比图](../evidence/week9/comparison/comparison.png)。
- [JMeter 脚本](../../performance/week9-comparison.jmx)、[复现与课堂展示步骤](../../performance/WEEK9.md)。
- [周推进计划](../todo/第9周推进计划.md)、[第八周交付](../week8/README.md)。

最终是否达标以 comparison.json 的 `all_three_targets_pass` 和原始 JTL 为准；不能只看截图或四舍五入后的宣传数字。

## 最终实测结论

2026-10-23 已完成两组各三轮正式测量，同环境校验通过，三个目标接口全部满足 p95 降低至少 20%、错误率不高于 1% 的要求。

| 接口 | 优化前 p95 | 优化后 p95 | 降幅 | 优化后错误率 |
| --- | ---: | ---: | ---: | ---: |
| 登录 | 8291 ms | 58 ms | 99.30% | 0% |
| 商品查询 | 3654 ms | 21 ms | 99.43% | 0% |
| 下单 | 3621 ms | 61 ms | 98.32% | 0% |

每接口每组 150 个正式样本、2 并发。前后吞吐量、各轮分位数、SQL 和资源数据见[完整统计](../evidence/week9/comparison/summary.md)。旧版登录/下单错误率均为 4%，这些失败仍计入统计。提升是本次多项改动的整体效果，不把改善比例归功于某一个索引，也不外推成高并发容量。

优化后每轮测量期请求 DDL 为 0，连接借出/归还数相等。分类查询使用 `ix_products_category_catalog`，执行计划不再出现 `Using filesort`。所有最终测试库均已清理，正式结果不包含冒烟、预热或被中断的不完整轮次。

## 如何确定基线

旧代码固定为第八周 `3a81987`，新代码复制为独立副本；两组均在同一 Windows/WAF、Waitress 4 线程、MySQL 8.0.43 和 LocMem 下运行。2 个独立交易用户、20000 件库存为 1 的二手商品，每组 3 轮，每接口合计 150 个正式样本。每轮新建相同数据的独立测试库，测完删除；真实库、真实私钥和课堂账号不参与压测。

前后保持相同 JMX、2 并发、1 秒请求间隔、口令算法和 2500 次迭代、连接池 10+20、认证/审计/限流。测量不经过 nginx/TLS，不能将本结果描述成 8443 生产容量。第八周 SQLite 小样本基线只留作历史，不用于本次改善比例。

## 改了什么、为什么

| 问题 | 本周实现 | 相关代码与验证 |
| --- | --- | --- |
| Python 循环执行 SM3/PBKDF2，登录占用 CPU | 探测 OpenSSL SM3 支持，使用原生 PBKDF2-HMAC-SM3/HMAC；SM3 空模板每次 copy，线程不共享可变摘要状态；不支持时保持旧算法回退 | [security.py](../../src/utils/security.py)；标准向量、Unicode/长口令、多块派生、2500 次旧摘要兼容、线程隔离测试 |
| 每次创建业务服务都检查表结构、初始化样例账号并生成 SM2 密钥 | 请求构造只创建业务对象；建表/种子改为显式管理命令；SM2 服务按需创建并读取已配置密钥，不随普通请求生成/覆盖密钥文件 | [unified_service.py](../../src/unified_service.py)；请求期 DDL 计数、无初始化/密钥生成回归 |
| SQLAlchemy 会话靠对象析构归还，时间不明确 | 请求作用域登记 service 会话，异常或正常返回均 finally close；非 HTTP 使用支持 with；保持连接池容量不变 | [database.py](../../src/Data_base/database.py)、[中间件](../../api_service/api/middleware.py)；即使外部引用 service 仍归还连接的测试 |
| 商品缓存保存 ORM 对象，失效时 Redis KEYS 或清空全部本地缓存 | 缓存普通 DTO，读库会话及时关闭；版本键失效，旧请求只能写旧版本，旧键 5 分钟自然过期；不清除其他 MFA/令牌状态 | [cache_utils.py](../../api_service/utils/cache_utils.py)；热查询无新增 SQL、并发失效、故障回源、下单刷新测试 |
| 分类查询过滤后排序，单字段索引不能覆盖整体访问路径 | 新增 active/available/created_at 及 category/active/available/created_at 复合索引，保留原索引；比较真实 MySQL EXPLAIN | [模型](../../src/Data_base/models/product.py)、[迁移](../../scripts/week9_create_indexes.py)，每轮 query-plan.json |
| 两人读取同一单件商品库存可能超卖 | 下单事务按商品 ID 一致顺序加 FOR UPDATE 行锁，并刷新商品快照后核对库存与计价 | [订单视图](../../api_service/api/views.py)、[并发实测](../evidence/week9/concurrency-verified/results.json) |
| MySQL 两个首次登录用户创建安全状态时死锁 | 先 INSERT ON DUPLICATE KEY UPDATE 原子建立记录，再进行锁定读取；重复记录只对主键做无变化更新，不重置已有 MFA、恢复码、锁定计数或版本 | [security_core.py](../../api_service/api/security_core.py)；5 轮同时冷登录、已有 MFA 与版本保留实测 |

没有缓存登录成功结果、密码派生结果或 JWT；没有减小迭代次数；没有把库存校验移到缓存。Redis 是任务允许的选项，本版不靠临时引入 Redis 改变前后环境。重点优化已有热路径并保留缓存故障回源。

本次测试证明现有算法结果兼容，并不等于对口令成本给出新的生产安全评级。保留 2500 次是为了公平比较；生产密码成本策略应独立评估，不能把“原生实现更快”等同“允许降低成本”。

## 正确性与安全回归

| 检查 | 记录 |
| --- | --- |
| 新性能正确性 + 第八周加固 + SM2 | [18 项测试](../evidence/week9/regression-final/security-tests.txt) |
| 第 2 周身份、MFA、权限 | [复测结果](../evidence/week9/regression-final/week2/results.json) |
| 第 4 周国密隧道、互通、篡改/重放 | [复测结果](../evidence/week9/regression-final/week4/results.json) |
| 银行模拟器与支付密钥互通 | [6 项银行测试](../evidence/week9/regression/payment-tests.txt)、[5 项离线配对检查](../evidence/week9/regression/payment-pair-check.json)；没有创建真实支付 |
| 真实 MySQL 双用户冷登录、同商品竞争、缓存、越权 | [并发记录](../evidence/week9/concurrency-verified/results.json)：两个登录均成功；订单状态 200/400；实际 1 单、库存 0、只售出 1 件 |
| 同范围生产 Bandit | [结果](../evidence/week9/regression-final/bandit-production.json)：保留 1 条 LOW 的 Swagger 无效 JWT 示例，无新增发现 |

前端源码和依赖本周未更换；没有伪称重新执行 Burp 全扫描或联网依赖扫描。依赖安全证据仍以第八周日期为准。

## 失败、异常和边界

- `smoke-before/`：隔离副本缺日志目录，服务未启动；夹具已补目录。
- `smoke-before-v2/`：未启用 Redis，但用要求 Redis 健康的接口等待就绪，最终超时；改用监听就绪，业务仍用 JMeter 断言验证。
- `before/`：旧版并发登录实际出现 MySQL 1213 死锁，原始请求失败和日志保留。
- `after-final/`：第一次优化后预热仍出现首次安全状态创建的间隙锁死锁，未计作通过；补上原子初始化后，重新执行安全回归与 `after-verified/` 的完整三轮。没有通过预先填充安全状态表来掩盖首次登录问题。
- `before-final/round-2-interrupted-*`、`after-verified/round-3-interrupted-*`：中断导致部分采样，单独保留且不计入正式指标；重启前核对指纹，已经完整完成的轮次不重复。
- 最终基线允许完整记录旧代码错误，优化后默认不允许任何失败。分析同时列出失败率，失败样本不剔除。
- MySQL 与其他项目共用一个实例，本实验只创建并清理独立测试库，未变更共用密码；不是独占物理机器的工业容量评估。

## 应用到现有本机环境

本机已在 2026-10-23 补建两个索引，迁移前商品表 32 行且无其他活动查询，迁移后商品行数不变，未更换共享密码，见[索引部署记录](../evidence/week9/deployment/indexes.json)。尚未替用户重启正在使用的后端进程，更新代码后按下面第 2 步重启。

1. 其他环境部署时，保存并备份现有数据库和配置，在维护窗口检查并创建两个新索引：

   ```powershell
   conda activate WAF
   python scripts/week9_create_indexes.py --dry-run
   python scripts/week9_create_indexes.py
   ```

   迁移仅添加缺少的命名索引，不删表、不改密码；重复运行不重复创建。新建测试库通过模型创建索引；实际业务库的迁移另有部署记录，两者独立核验。
2. 更新代码后重启本项目后端：`python scripts/serve_backend.py`。前端源码未改，不需要迁移框架或重新生成客户端证书。
3. 已有库不再在每次请求时自动建表/补样例；新环境先执行 `python api_service/manage.py init_security`，课堂账号用 `seed_week1` 交互创建，见[启动说明](../../HowtoRun.md)。
4. 原有 keys 保留。独立 SM2 加解密教学功能需提前配置其密钥，登录、商品与订单请求不再偷偷生成或替换它们。
5. 验证登录、商品、下单和管理员页面，再按需补测 HTTPS 8443 端到端性能。不得把独立实验的 LocMem/HTTP settings 替换进生产配置。

源代码回退不会自动删除新索引；这些索引不改变数据语义。若需移除，先核对索引名和实际使用情况，再安排迁移窗口，不能重置数据库来回退性能改动。
