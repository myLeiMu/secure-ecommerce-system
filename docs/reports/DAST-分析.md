# Burp DAST 报告分析

核对日期：2026-10-07。来源为用户提供的 `DAST.html`。提交时使用 [DAST-脱敏.html](DAST-脱敏.html)；原报告含 2 个不同的完整 JWT 及用户资料，仅本机保留。脱敏副本移除了 HTTP 正文、认证和 Cookie 头，并替换其他位置的邮箱及 JWT，原始正文复现需在 Burp 私有项目中核对。

## 实际结果与范围

高危 0、中危 0、低危 1、信息项 25，共 26 个实例、7 类。低危为 Certain；信息项中 Certain 17、Firm 7、Tentative 1。

目标为 `http://localhost:3000`，包含开发服务器 HTML/JS 与代理后的 API。管理员、审计查询和个人资料存在带 Bearer 的 200 JSON 响应，也有改变路径和转发头的主动探测证据。报告没有扫描任务配置、起止时间、完整审计清单和各角色登录流程，不能据此宣布全站或三个角色已完整扫描；未覆盖 HTTPS 8443 的 TLS、mTLS 及 nginx 响应头。

## 逐项研判

| 类别 | 数量 / Burp 级别 | 判断与后续操作 |
| --- | --- | --- |
| Unencrypted communications | 1 / Low | 3000 是 HTTP 开发入口，通信未加密；不能推断 8443 也未加密。应另扫 8443，并确认正式部署只开放预定 HTTPS 入口。 |
| CSP: allows clickjacking | 1 / Information | `/products` 的 301 重定向响应缺少 `frame-ancestors`，与下面防嵌入问题关联，勿重复计为两类已利用漏洞。 |
| Cross-origin resource sharing | 12 / Information | 示例 Origin 为 `http://localhost:3000`，响应允许同一来源并带 credentials，只证明配置 CORS。应使用恶意 Origin 复测；代码中 localhost 任意端口规则应按部署需求评估缩小。 |
| Input returned in response | 1 / Information | 路径标记出现在开发服务器 404 HTML。反射标记本身不是 XSS，需确认转义和浏览器执行上下文。 |
| Request URL override | 1 / Information, Tentative | 注入外部转发 Host 后从 200 变成 400，无外部重定向或回连证据。`USE_X_FORWARDED_HOST=True` 与 Host 白名单拒绝一致，尚未确认可利用漏洞；需核查代理是否清理客户端转发头。 |
| Frameable response | 7 / Information, Firm | `/`、`/agreement`、`/contact`、`/help`、`/privacy`、`/products/`、`/robots.txt` 缺少防嵌入头；API 则已有 `X-Frame-Options: DENY`。应在前端服务器及 nginx 配置 HTML 防嵌入头，再用 iframe 和复扫验证；敏感操作诱导尚未证实。 |
| Email addresses disclosed | 3 / Information | `/`、`/api` 是聚合路径，实际证据是带认证的管理员用户列表和个人资料，并非匿名访问首页就能读取用户列表；第三方 JS 另有示例邮箱。需用无 JWT 和交易用户 JWT 验证管理员接口权限。 |

## 覆盖限制与下一轮证据

订单请求有一个 429 证据，限流影响了至少部分探测。降低并发、增加间隔并在限流窗口结束后复扫订单接口，保留原 429 证据，不应为扫描直接关闭正式限流。

本报告未确认 SQL 注入、可执行 XSS、资源归属越权或任意来源 CORS 泄露。“未报告高/中危”不等于系统没有此类漏洞。补充 Dashboard 完成状态、配置及审计清单，两名交易用户的订单归属对照、交易用户/审计员到管理员接口的角色对照，以及登出后 JWT 重放证据。

本次完成报告研判，尚未修复新增问题或生成修复后 Burp 报告。已有依赖和支付密钥等待处理项继续见 [漏洞清单](../第7周漏洞清单.md)。
