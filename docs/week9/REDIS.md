# 第九周 Redis 补充实验

日期：2026-10-28。保留二手交易平台的交易用户、管理员、审计员三身份。本次只扩展实验脚本和证据，不更换业务密码、不重启业务后端、不执行 Git 暂存或提交。

## 结果入口

- [后续 10 / 30 并发实验](HIGH_CONCURRENCY.md)：使用无思考等待的独立容量配置，不混入本页 2 并发数据。
- [LocMem 与 Redis 对比](../evidence/week9/cache-comparison-20261028/summary.md)
- [机器可读统计](../evidence/week9/cache-comparison-20261028/comparison.json)
- [接口 p95 与缓存命中率图](../evidence/week9/cache-comparison-20261028/comparison.png)
- [Redis 原始结果](../evidence/week9/redis-20261028/)、[本次 LocMem 对照](../evidence/week9/locmem-20261028/)
- [原第九周优化前后对比](../evidence/week9/comparison/summary.md)

正常启动项目原本使用 django-redis。本次连接检查确认 WSL Redis 6.0.16 在项目已配置地址可用，认证 PING 成功。此前连接超时不能作为当前不可用的依据；本次没有修改 Redis 服务配置或 `.env`。

本次两组均使用相同的优化后业务代码、相同 JMX、20000 件虚构单库存商品、2 并发、3 轮，每接口每组 150 正式样本。除缓存后端外固定实验配置一致，并核对源码、依赖和环境摘要。冒烟和预热另存，错误样本不剔除。

这是“同一代码选择两种缓存”的补充实验。原报告是“旧代码与优化代码”的验收实验，两个问题的结论独立；不能将旧 LocMem 基线与新 Redis 数字混合并宣称全部提升来自 Redis。

## Redis 数据如何隔离和核实

每轮使用独立 MySQL 测试库，以及同名随机 `test_week9_` Redis 键前缀。测试流量访问独立 HTTP 8769，不使用真实课堂账号和商品。Redis 密码仅通过子进程环境传递，报告不写入密码、缓存值或 JWT。

在真实缓存后端的 `get` 方法外统计商品数据键命中、未命中和异常；不把频繁读取的版本键计入命中率。两组使用完全相同的统计代码。每轮保留 `redis-evidence.json`，包括 PING、专属键数量、商品键数量和 TTL；同时记录真实订单数、负库存检查及 SQL 次数。

商品数据有效期 300 秒；下单后旋转缓存版本，旧缓存自然到期。此流程每次查询后都发生下单，因此频繁失效，不能把它当作纯只读热点的命中率。Redis 涉及跨 Windows/WSL 通信，当前单进程低并发负载下未必快于 LocMem；多进程共享能力不在本次容量验证范围内。

结束时仅 SCAN 并删除本轮随机前缀，保存 `redis-cleanup.json`，要求剩余键数为 0。不执行 FLUSHDB、FLUSHALL，不清理业务的 `ecommerce` 前缀。执行器禁止把旧代码直接用于共享 Redis 测试，因为旧缓存失效代码可能扫描其他命名空间。

## 复现与课堂演示

在项目根目录激活 WAF，确认 WSL Redis 与 MySQL 已启动，`.env` 保留正确连接参数。输出目录必须是新目录；前一条完成后再执行下一条，避免相互争抢资源。

```powershell
conda activate WAF
python scripts/week9_perf.py --source-ref WORKTREE --cache redis --output docs/evidence/week9/redis-new
python scripts/week9_perf.py --source-ref WORKTREE --cache locmem --output docs/evidence/week9/locmem-new
python scripts/compare_week9_cache.py --locmem docs/evidence/week9/locmem-new --redis docs/evidence/week9/redis-new --output docs/evidence/week9/cache-comparison-new
```

需要先做短验证时加 `--smoke-only`，但仅冒烟的数据不能生成完整三轮比较报告。恢复中断的实验使用 `--resume`，要求配置和源码摘要保持一致；不要并行启动或恢复同一输出目录。

课堂上依次展示：

1. 正常运行的缓存配置与实验脚本的 `--cache` 参数，说明两种后端如何切换。
2. 两组 `environment.json`，指出相同源码/JMX 与唯一计划变化项——缓存后端。
3. 对比报告的三个目标接口及购物车准备步骤；解释 p95、吞吐量和错误率口径。
4. `redis-20261028/round-1/redis-evidence.json`，证明有实际商品缓存及有效期；配合 `results.json` 的缓存命中统计。
5. `redis-cleanup.json` 和 `cleanup.json`，证明测试缓存和 MySQL 夹具已清理。

正常运行仍使用原启动命令与 WSL nginx；`week9_settings.py` 是隔离测试专用配置，不能替换正式 settings。当前实验没有证明 nginx 8443 的端到端性能或多进程高并发容量。
