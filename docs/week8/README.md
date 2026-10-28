# 第八周交付说明与验收索引

交付日期：2026-10-22。项目：安全二手交易平台；业务身份：交易用户、管理员、审计员。本文是本周提交的入口；历史报告保持原日期，不用新结果覆盖旧证据。

## 1. 本周交付结论

已形成“漏洞修复提交 → 前后对比 → 回归记录”的证据链；完成第 2/4 周改动后回归以及 JMeter 三接口冒烟和初始基线。最新收到的 Burp 导出摘要为零发现，但报告没有记录扫描范围；共享数据库旧密码仍待协调轮换。因此本版可作为**包含明确待办的第八周交付**，不能标记“所有风险已清零”。

第九周优化尚未开始，本版不声称 p95 已改善 20%。

## 2. 修复提交与实现

在原仓库可执行 `git show --stat 73102fa`、`git show --stat baae308` 查看修复范围。无历史源码包内不含这些 Git 对象，应在原课程仓库关联对应提交；不能把源码包的新初始提交当成全员协作记录。

| 提交 | 内容 | 关键代码 |
| --- | --- | --- |
| `73102fa` | Python 依赖升级、原生 SM4-GCM、RSA 安全随机数、支付密钥默认值清理和配套轮换、早期网关加固、基线准备 | [隧道](../../src/crypto_tunnel.py)、[基线驱动](../../scripts/week8_perf.py) |
| `baae308` | Vite/Vitest 迁移、HTTPS/CSP 与可信代理、银行卡字段加密、SM2 C3/随机数/曲线点验证、回归证据 | [Vite](../../frontend/vite.config.mjs)、[中间件](../../api_service/api/middleware.py)、[加密字段](../../src/Data_base/encrypted_fields.py)、[SM2](../../src/utils/secure_sm2.py) |
| 本次交付整理提交 | 最终索引、启动文档、无秘密配置模板、后续 Burp 报告分析与发布检查；移出本地覆盖率和加密私钥缓存的跟踪 | 根目录 README、HowtoRun、本文及 docs/reports；用 `git log -1` 查看提交号 |

前后对比详见 [2026-10-21 整改报告](../reports/2026-10-21-漏洞整改与复测.md)。

## 3. 验收证据表

以下结果引用实际保存的测试记录，不表示交付当天重新执行了每一项测试。最终安全回归日期为 2026-10-21，初始性能记录为 2026-10-17；本次以文档和发布整理为主。

| 检查 | 结果 | 原始证据/说明 |
| --- | --- | --- |
| npm 全依赖 | 51 → 0 条 | [before](../evidence/remediation-20261021/npm-before.json)、[after](../evidence/remediation-20261021/npm-after.json) |
| WAF pip-audit | 最后 certifi 告警 1 → 0 条 | [before](../evidence/remediation-20261021/pip-before.json)、[after](../evidence/remediation-20261021/pip-after.json) |
| Bandit 生产范围 | 剩 1 个 LOW，不完整 Swagger JWT 示例，无有效签名 | [生产扫描](../evidence/remediation-20261021/bandit-production.json) |
| Bandit 扩大范围 | 11 项：9 个测试 assert、1 个无效测试摘要、1 个 Swagger 示例 | [扫描结果](../evidence/remediation-20261021/bandit-after.json)，未用批量 nosec 隐藏 |
| Burp Professional | 第一次修复后 18 实例；第二次 4 实例；第三份导出 0 实例，范围不可直接等同 | [第二次分析](../reports/DAST-fixed-twice-分析.md)、[第三次分析](../reports/DAST-fixed-tri-分析.md) |
| 第 2 周权限/身份回归 | 28 项通过 | [results.json](../evidence/remediation-20261021/week2/results.json) |
| 第 4 周国密隧道回归 | 20 项通过，含互通、重放与篡改拒绝 | [results.json](../evidence/remediation-20261021/week4/results.json) |
| 新安全与 SM2 回归 | 9 项通过 | [测试记录](../evidence/remediation-20261021/hardening-tests.txt) |
| 银行、支付配对 | 6 项银行测试 + 5 项配对检查通过 | [银行测试](../evidence/remediation-20261021/payment-tests.txt)、[配对](../evidence/remediation-20261021/payment-pair-check.json) |
| 前端 | 23 项测试通过，生产构建成功 | [测试](../evidence/remediation-20261021/frontend-tests.txt)、[构建](../evidence/remediation-20261021/frontend-build.txt) |
| 生产页面浏览器 | 7 组流程通过，无 JS/CSP 错误 | [结果与截图目录](../evidence/remediation-20261021/browser/) |
| HTTPS 网关 | 最终 17 项通过；启动窗口失败记录另外保留 | [最终结果](../evidence/remediation-20261021/https-gateways.json) |
| 有限 HTTP DAST | 10 请求回归 | [结果](../evidence/remediation-20261021/dast-regression.json)，不能替代 Burp 全扫描 |
| 卡号迁移 | 迁移 1 行，剩余明文 0；重复迁移 0 行 | [迁移](../evidence/remediation-20261021/card-migration.json)、[幂等](../evidence/remediation-20261021/card-migration-idempotent.json) |

依赖扫描“0”仅代表扫描当时的版本和漏洞库。生产与测试范围的 SAST 数量不同，比较时必须保持扫描参数一致。

本次交付整理另有[发布检查记录](../evidence/week8-delivery-20261022/release-check.json)和[运行依赖离线 dry-run](../evidence/week8-delivery-20261022/runtime-requirements-check.txt)。检查覆盖当前候选文件中的配置秘密值/完整 JWT/PEM 私钥、文档链接、JMX XML、忽略规则及被移出跟踪文件的内容保留；不扫描 Git 旧历史，也不替代全新机器安装或新的安全扫描。

## 4. JMeter 初始基线

[JMX](../../performance/week8-baseline.jmx) → [使用说明](../../performance/README.md) → [完整数据与 CPU/RSS](../evidence/week8/performance-final/) → [摘要表](../evidence/week8/performance-final/summary.md)。

环境为隔离 HTTP/SQLite/wsgiref，1 并发，1 秒启动，每次请求前暂停 1000 ms；每轮 2 次预热、10 次测量，三轮。登录使用真实 SM3-PBKDF2 的 2500 次计算；真实创建测试订单并检查购物车清空。不要降低密码计算成本来制造性能改善。

| 轮次 | 登录 p95 / 吞吐 | 商品查询 p95 / 吞吐 | 下单 p95 / 吞吐 | 三接口错误率 |
| --- | --- | --- | --- | --- |
| 1 | 3194 ms / 0.1491 req/s | 9 ms / 0.1591 req/s | 13 ms / 0.1592 req/s | 0% |
| 2 | 2944 ms / 0.1513 req/s | 10 ms / 0.1605 req/s | 14 ms / 0.1606 req/s | 0% |
| 3 | 2992 ms / 0.1520 req/s | 9 ms / 0.1607 req/s | 16 ms / 0.1608 req/s | 0% |

这是低负载流程基线，吞吐含流程间隔，不是饱和 QPS。10 个样本的 nearest-rank p95 等于最大值。第九周如使用实际 MySQL/Waitress/nginx，必须重新测同环境优化前基线，不能拿本表直接算提升比例。

## 5. 课堂展示顺序

1. 打开本页，说明三身份及本周范围；展示两个修复提交，任选 SM2 C3 校验或银行卡加密字段解释输入、处理和失败行为。
2. 并排打开 npm/pip before/after；打开 Bandit 生产结果，解释唯一 LOW 为什么不是可用凭据。不要将“LOW 数量不为零”说成扫描未运行。
3. 打开三份脱敏 Burp 报告及分析。最新报告为零发现，同时展示实际 Burp 任务范围、完成状态和认证覆盖；当前仓库还缺这些范围截图，现场补证时遮盖令牌与个人资料。
4. 用 HTTPS 8443 演示交易用户、管理员、审计员权限；管理员/审计员 TOTP，证书登录仍由 nginx mTLS 验证。依照[整改报告第四节](../reports/2026-10-21-漏洞整改与复测.md#4-最新启动与-burp-复扫)演示匿名 401、非管理员 403、明文敏感 POST 426。
5. 展示第 2/4 周结果文件；解释隧道篡改和重放如何被拒绝，不将登录成功等同完整安全回归。
6. 在 JMeter 打开 JMX，展示 login/products/order 与购物车准备步骤、业务断言和样本结果；展示本表和环境指纹。不把 GUI 人工点击产生的新样本混进已保存基线。
7. 最后说明共享密码协调、Burp 范围补证和第九周同环境复测三项后续工作。

## 6. Git 上传与源码包

提交内容包括源码、前端锁文件与生产构建、JMX、文档、脱敏报告及测试证据。排除 `.env`、`keys/`、本地加密私钥缓存及备份、原始 Burp 报告、`node_modules/`、覆盖率缓存和发布 ZIP。本机被移出跟踪的文件仍然保留。

### 继续已有课程仓库

本地分支为 `codex/week8-hardening-baseline`。先查看最新提交和改动，再由组员自行推送和创建 PR：

```powershell
git status --short
git log -3 --oneline
# 确认远端可见性、历史凭据处理和小组协作安排后，再执行：
git push -u origin codex/week8-hardening-baseline
```

**原分支保留旧 Git 历史，其中的共用 MySQL 旧密码仍有效。不能将该分支直接当作可公开发布的无凭据历史。** 本次不自动推送、不改密码、不重写历史。按[协调步骤](../reports/2026-10-21-漏洞整改与复测.md#5-共用数据库密码协调步骤本轮不改密)完成轮换；如需清理历史，与组员协商后另行执行，历史清理不能替代轮换。

### 只上传本次源码快照

交付 ZIP 由最终提交的 `git archive` 导出，包含本周文档，不包含 `.git` 和旧提交。解压到**新目录**，不要覆盖现有项目或 `.env`。若老师允许独立快照仓库，可在该新目录初始化并关联新仓库：

```powershell
git init -b main
git add .
git commit -m "docs: deliver week 8 source and security evidence"
git remote add origin <新的课程仓库地址>
git push -u origin main
```

快照不携带历史凭据，但不能消除旧仓库已经发生的泄露；原仓库的协作提交仍应留存用于课程审查。源包不含实际数据库、私钥或课堂账号密码，新环境按[启动文档](../../HowtoRun.md)单独配置。

## 7. 明确保留的待办

- 共用 MySQL 旧密码失效：用户明确暂缓，需协调所有使用方，不能以“无影响”关闭。
- Burp 范围证据：第三份报告没有目标/认证覆盖信息，不能证明 8443、三角色与所有接口均复扫；补任务截图/配置和必要复扫，不改写原报告。
- 历史 SM2 业务证书并未全部重签；本轮加固后新生成密钥使用安全随机源，不能宣称所有历史密钥换新。
- 模拟银行仅用于本机课堂，当前独立开发服务不是对外生产银行部署。
- 第九周性能优化与同环境对照尚未完成；本周只交付初始参考基线。
