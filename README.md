# 安全二手交易平台

《进阶式挑战性综合项目 III：安全电子商务系统的设计与实现》课堂项目。交易用户同时买卖二手商品，业务身份只有 **交易用户 `normal`、管理员 `admin`、审计员 `auditor`**。历史 `merchant` 数据兼容不增加第四种业务身份。

## 从这里开始

- **[第九周性能基线与优化](docs/week9/README.md)**：JMeter 三接口、MySQL 前后对比、监控与正确性回归。
- [Redis 补充实测与课堂演示](docs/week9/REDIS.md)：相同优化后代码的 LocMem / WSL Redis 对照、缓存命中率和隔离清理证据。
- **[第八周交付说明与验收索引](docs/week8/README.md)**：修复提交、扫描、回归、性能准备和待办。
- **[启动与新机器配置](HowtoRun.md)**：WAF、WSL nginx、HTTPS 和本地配置。
- [漏洞整改与前后对比](docs/reports/2026-10-21-漏洞整改与复测.md)
- [最新 Burp 零发现报告的范围说明](docs/reports/DAST-fixed-tri-分析.md)
- [JMeter 使用方法与环境限制](performance/README.md)
- [第八周计划与完成情况](docs/todo/第8周推进计划.md)

## 本版内容

保留注册登录、证书登录、TOTP 二维码、三角色权限、商品发布与交易、管理控制台和审计功能。第八周补齐依赖升级、HTTPS/CSP、可信代理、银行卡存储加密、SM2 随机数及完整性校验，并重跑第 2 周、第 4 周安全回归。JMeter 已建立登录、商品查询、下单的隔离低负载初始基线。

已验证环境为 Windows + WAF Python 3.13.5、Node 22.20.0、WSL Ubuntu nginx；后端 Django/DRF + SQLAlchemy/MySQL + Waitress，前端 Vue 3 + Vite/Vitest。具体版本以锁文件和证据中的环境记录为准。

已有本机环境分别开启终端：

```powershell
# 先启动 WSL，再在项目根目录启动后端
conda activate WAF
python scripts/serve_backend.py
```

```powershell
cd frontend
npm ci
npm run dev
```

开发入口 **https://localhost:3000**；课堂生产构建及浏览器证书登录入口 **https://localhost:8443**。课堂入口需要 `npm run build` 和已配置的 WSL nginx，不能直接用 HTTP 3000 替代。

## 验收边界

2026-10-21 保存的 npm/pip 扫描均为 0 条依赖漏洞；最新 Burp 导出摘要为 0 条发现，但不包含目标与扫描覆盖记录，不能据此宣称所有接口已覆盖。第九周的固定课堂负载实测见性能交付报告；它不代表高并发容量或 nginx 8443 端到端成绩。

**共用 MySQL 密码按用户要求暂不轮换，旧 Git 历史仍含有效旧凭据。** 当前源码已移除该密码；不得把含旧历史的仓库当作可公开发布的干净仓库。上传前见交付说明中的历史处理办法。本项目不提交 `.env`、私钥、原始认证抓包或本地数据库。

## 团队与协作

沿用原仓库成员记录：myLeiMu（算法实现）、diomand-bo（测试验证）、wnsjdh（文档编写）、Eddiez0616（系统集成）。本周责任认领见推进计划，实际贡献以本人提交和 PR 为准。

提交信息使用 `feat:`、`fix:`、`docs:`、`test:` 等类型；每项修复应关联前后对比和回归证据。禁止将账号密码、令牌或证书私钥放入提交、Issue 和截图。
