# 第二次修复后 Burp 报告分析

报告：DAST-fixed-twice.html；Burp Professional 2026.4.3；报告生成时间：2026-10-21 23:28:24（北京时间）。本次目标为 **https://localhost:3000**，不包含 nginx 8443 的完整验收。

## 结果

共 2 类、4 个实例：0 高危、1 中危、0 低危、3 信息项。前一份报告中的明文通信、CSP 脚本/样式/表单限制、CORS 告警本次未再报告。两个报告的协议和范围不同，不能仅凭数量下降宣称覆盖相同，也不能证明不存在报告外问题。

| 项目 | 结论 | 后续处理 |
| --- | --- | --- |
| TLS certificate，Medium/Certain | 报告明确原因是服务端证书不受信任；签发者为 Secondhand Classroom Local CA。没有报告过期或主机名错误。 | 配置 Burp 对课堂 CA 的信任，再新建扫描任务复查。不能直接把证书信任问题标成无影响。 |
| Email addresses disclosed，分组 `/` | 实际请求是带 Bearer 的 GET /api/admin/users，属于管理员用户列表。分组路径并不表示匿名首页泄露全部邮箱。 | 保留管理员正常功能，并以匿名 401、交易用户/审计员 403、管理员 200 的权限测试作为依据。 |
| Email addresses disclosed，分组 `/api` | 包含带 Bearer 的 GET /api/users/profile 与 GET /api/admin/users；报告没有提供越权读取证据。 | 个人资料只给本人，用户列表只给管理员；沿用权限回归，不能仅凭检出邮箱认定漏洞。 |
| Email addresses disclosed，qrcode.js | 路径为 `/node_modules/.vite/deps/qrcode.js`，属于 Vite 开发依赖。 | 属于第三方库中的邮箱文本，不删除库版权说明来消除扫描提示。课堂发布验收应补扫生产构建的 8443。 |

本次额外核对本机 localhost.crt：签名可由 classroom-ca.crt 验证，证书在当前有效期内，SAN 包含 localhost 和 127.0.0.1。该检查证明本机证书与本机 CA 匹配，不代表 Burp/浏览器已经信任该 CA。

## 配置 Burp 的课堂 CA 信任

1. 打开 **Settings → Network → TLS → Custom CA certificates → Add**。
2. 添加本项目公开 CA 证书：`D:\Coding\secure-ecommerce-project\keys\mtls_local\classroom-ca.crt`，核对其主题为 Secondhand Classroom Local CA。这里只需 CA 证书，不需要上传私钥。
3. 重启 Burp，重新访问 https://localhost:3000，再建立新扫描任务，确认 TLS certificate 告警是否消失。既有报告不会因配置更新自动改变。
4. 如果仍出现同一告警，核对 Burp 实际看到的签发者及其正在使用的信任配置；保留新报告，不靠禁用校验或勾选误报隐藏问题。

官方说明：Custom CA certificates 管理 Burp 验证上游 TLS 时信任的额外 CA，属于用户设置，会影响该机器上的 Burp 安装。[PortSwigger TLS 设置](https://portswigger.net/burp/documentation/desktop/settings/network/tls#custom-ca-certificates)。添加 CA 并重启的操作见 [PortSwigger 官方排障步骤](https://portswigger.net/burp/documentation/desktop/extend-burp/extensions/troubleshooting)。

三个证书用途要分清：课堂 CA 让 Burp 信任本站服务端；Burp CA 让外部浏览器信任抓包代理；课堂账号的 P12 是浏览器证书登录身份，配置在 Client TLS certificates。信任 Burp CA 不能代替信任本站 CA。

本地课堂可以使用自行管理、明确受信的 CA；正式公网部署须使用适合实际域名和客户端信任体系的服务端证书。关闭校验不是修复。

## 还需要补齐

- 对 https://localhost:8443 单独扫描，保留交易用户、管理员、审计员的认证有效证据；3000 的报告不能替代 nginx/mTLS 网关验收。
- 按用户先前明确要求，共用 MySQL 密码没有修改，历史凭据仍有效。它不属于无影响项，按 [整改记录第五节](2026-10-21-漏洞整改与复测.md#5-共用数据库密码协调步骤本轮不改密) 协调轮换。
- 本报告含 Bearer 和用户邮箱，原件保留本机并加入 .gitignore；[脱敏副本](DAST-fixed-twice-脱敏.html) 删除原始请求/响应块、JWT 与邮箱，适合提交课堂证据。

本轮完成报告研判与本机证书核验，没有擅自修改 Burp/系统信任库，没有改数据库密码，也没有生成新的 Burp 扫描结果。
