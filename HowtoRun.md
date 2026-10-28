# 第八周版本启动与环境配置

> 第九周更新：启动入口保持不变；请求不再自动建表或生成 SM2 密钥。新环境仍先执行下文 init_security/seed_week1。已有环境的复合索引迁移和代码更新见[第九周部署说明](docs/week9/README.md#应用到现有本机环境)。保留现有 `.env` 和 keys。

对应版本：[第八周交付索引](docs/week8/README.md)。旧的 HTTP 3000、Vue CLI 和直接 runserver 8080 说明已被本页替代。以下默认 Windows 项目目录 `D:/Coding/secure-ecommerce-project`，nginx 在 WSL Ubuntu-22.04；换机器必须调整路径和 WSL 网卡地址。

## 1. 已有本机环境日常启动

保留现有 `.env`、数据库和 `keys/`，不要复制模板覆盖它们，不要重新生成银行卡、TOTP 或隧道加密密钥。

1. 启动 WSL、MySQL 和已配置的 nginx。WSL 内可用 `sudo nginx -t` 检查配置；已有服务用 `sudo service nginx start` 启动。不要更改其他项目的 80 端口服务。
2. 在项目根目录、WAF 环境启动电商后端：

   ```powershell
   conda activate WAF
   python scripts/serve_backend.py
   ```

   后端监听 127.0.0.1:8080 和 Windows 的 WSL 专用网卡，不监听所有网卡。找不到 WSL 网卡时先启动 WSL；网卡地址变更后还要同步 nginx upstream。不要同时启动旧 runserver 占用 8080。
3. 课堂展示使用生产构建：

   ```powershell
   cd frontend
   npm ci
   npm run build
   ```

   打开 **https://localhost:8443**。nginx 直接服务 `frontend/dist`，此模式不需要运行 Vite。
4. 需要前端热更新时，在 frontend 另开终端运行 `npm run dev`，打开 **https://localhost:3000**。证书登录按钮转到 8443；3000 不是 nginx mTLS 入口。
5. 演示支付时，另一个 WAF 终端在项目根目录执行：

   ```powershell
   python bank_service/manage.py runserver 127.0.0.1:8001
   ```

   本机 `.env` 的 BANK_PAY_BASE_URL/BANK_REFUND_URL 应对应 8001，支付回跳到 HTTPS 8443，因此完整支付演示也从 8443 登录开始。模拟银行仅用于本机课堂。

| 地址 | 用途 |
| --- | --- |
| https://localhost:8443 | nginx 生产前端、同源 API、浏览器证书验证 |
| https://localhost:3000 | Vite 开发前端及同源代理，需要本地 TLS 文件 |
| http://127.0.0.1:8080 | 内部电商上游；不是浏览器业务入口，敏感明文请求被拒绝 |
| http://localhost:8088 | 跳转至固定 HTTPS 8443 |
| http://127.0.0.1:8001 | 仅本机模拟银行 |

## 2. 新机器获取源码后

源码包和 Git 都不提供实际账号密码、数据库、私钥或认证抓包。以下属于新安装操作，**已有环境跳过**。本次没有在另一台空白机器完整复现部署，不能把环境模板视为一键部署保证。

### 运行依赖

本版实际验证 Python 3.13.5、Node 22.20.0。新建独立 WAF 环境后，在项目根目录执行：

```powershell
python -m pip install -r docs/requirements/runtime-week8.txt
python -m pip install -r docs/requirements/security-tools.txt
cd frontend
npm ci
```

[runtime-week8.txt](docs/requirements/runtime-week8.txt) 是按现有 WAF 实装版本整理的应用直接依赖与关键补丁约束，不是含全部传递依赖及哈希的跨平台锁文件。[requirements.txt](docs/requirements/requirements.txt) 是历史环境快照，包含 Conda/科学计算包，不应原样作为任意机器的 pip 安装清单。JMeter 还需单独安装 Java/JMeter，见 [performance/README](performance/README.md)。

### 数据库、密钥和账号

1. 在数据库管理工具创建电商库 `ecommerce_system` 和银行库 `mock_bank_service`，使用各自仅可访问本库的应用账号。实际密码在本地配置，不提交 Git。
2. 仅在根目录尚无 `.env` 时，把 `.env.example` 复制为 `.env`，填写数据库连接。BANK_DB_USERNAME/PASSWORD 是独立配置，空值不会自动继承电商账号；两套都要填写。
3. 进入 Python 交互解释器，执行以下代码生成缺失的 Django 密钥，不输出密钥，不覆盖已有值：

   ```python
   import secrets
   from dotenv import dotenv_values, set_key
   config = dotenv_values('.env')
   for name in ('DJANGO_SECRET_KEY', 'BANK_DJANGO_SECRET_KEY'):
       if not config.get(name):
           set_key('.env', name, secrets.token_urlsafe(48))
   ```

   退出解释器后运行 `python scripts/setup_security.py`，生成缺失的 JWT、代理和 TOTP 加密密钥。新环境无旧账号可使用这一步；恢复旧数据库必须恢复原 MFA/卡号/隧道密钥，不能用新钥代替。
4. 创建结构并生成新环境的必要密钥：

   ```powershell
   python api_service/manage.py init_security
   python scripts/encrypt_stored_cards.py
   python scripts/setup_tunnel.py
   python api_service/manage.py seed_week1
   ```

   seed_week1 交互输入新课堂账号密码，不使用公开固定密码参数；已有账号保持不变。它创建三个业务身份，多名卖家测试账号仍是 normal。主要演示账号为 week1_admin、week1_auditor、week1_buyer。管理员和审计员首次登录按界面绑定 TOTP，二维码与手动密钥等价。
5. 如需新环境支付，先初始化银行库 `python bank_service/manage.py migrate`，再用 `python bank_service/manage.py seed_bank` 创建仅供课堂的测试数据。**仅新环境初始化时**执行 `python scripts/rotate_payment_keys.py --rotate` 配置电商与银行的配对商户密钥；已有环境不要重复执行，尤其不能在待支付订单仍有效时随意换钥。

`.env` 和 `keys/` 需要私下加密备份；绑定账号、证书及数据库状态也需匹配。恢复加密数据库但丢失原密钥时，应停止恢复流程，不把密文当明文或重新生成密钥强行启动。

### 新环境 WSL nginx 与证书

1. 启动 WSL，在 Windows 查看专用网卡：

   ```powershell
   Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -like '*WSL*' } | Select-Object InterfaceAlias,IPAddress
   ```

2. 在项目根目录运行 `python scripts/prepare_wsl_mtls.py --backend-ip <实际WSL网卡IPv4>`。它生成本机 CA、localhost 证书、三个课堂账号 P12、代理 secret include 和 nginx 配置，位于忽略的 `keys/mtls_local/`。不要把这些文件上传仓库。
3. 在 WSL 安装好 nginx 后，将生成的 `nginx-site.conf` 安装为本项目站点，`proxy-secret.conf` 安装到 `/etc/nginx/snippets/secondhand-mtls-secret.conf`（仅 root 可读）。例如，**仅新安装且目标文件尚不存在**：

   ```bash
   sudo install -d -m 755 /etc/nginx/snippets
   sudo install -m 600 /mnt/d/Coding/secure-ecommerce-project/keys/mtls_local/proxy-secret.conf /etc/nginx/snippets/secondhand-mtls-secret.conf
   sudo install -m 644 /mnt/d/Coding/secure-ecommerce-project/keys/mtls_local/nginx-site.conf /etc/nginx/sites-available/mtls_demo.conf
   sudo ln -s /etc/nginx/sites-available/mtls_demo.conf /etc/nginx/sites-enabled/mtls_demo.conf
   sudo nginx -t
   sudo service nginx start
   ```

   已有配置先备份并核对，不能覆盖其他项目站点。若默认 nginx 80 站点与其他服务冲突，只调整本项目新安装的默认站点配置，不停止别人的服务。项目站点使用 8443 和 8088。已有 nginx 配置应用加固见[整改报告](docs/reports/2026-10-21-漏洞整改与复测.md)。
4. Windows/浏览器信任 `classroom-ca.crt`；按需导入对应账号 P12，导入口令见本机配套 `*.import-password.txt`。P12 是私密身份材料，不在课堂投屏或文档中展示口令。
5. nginx 验证证书信任链，后端通过受信代理读取客户端证书 CN，并与已有用户名匹配；角色从数据库读取，不由证书赋予。管理员和审计员还需完成账号的 TOTP 绑定。按[证书登录与手动课堂演示](docs/todo/证书登录与手动课堂演示.md)验证证书选取、用户名匹配和 MFA；更换 CA 后要同步浏览器、nginx 与 Burp 的信任配置。

## 3. Redis 与测试边界

Redis 连接失败时代码有进程内缓存回退，但多进程共享状态和持久性不等价，不能把回退模式当成正式多实例部署。沿用本机已配置 Redis 即可；新配置应绑定回环或必要的专用接口、保留 protected-mode、设置凭据及访问限制，**不要照搬旧文档的 bind 0.0.0.0 / protected-mode no**。第九周需把是否启用 Redis 写入冻结环境。

需要 Swagger 时使用 HTTPS 8443 的 `/api/swagger/`，用实际登录令牌临时授权，不能复制到仓库。安全复测与第八周演示见[交付说明](docs/week8/README.md)；原始 Burp 报告含认证信息，仅提交审核后的脱敏副本。

## Windows 开发端口被保留（EACCES）

项目按用户要求继续使用 **https://localhost:3000**。2026-10-28 本机 IPv4/IPv6 TCP 排除段 2988–3087 包含 3000，两种地址均实际绑定失败；动态端口范围为 1024–65534。切换监听地址不能解决。

当前 Codex 进程没有 Windows 管理员权限，尚未修改系统网络设置。先保存任务并暂停 WSL/Docker 中需要保持连接的工作，再以管理员身份打开 PowerShell，在项目根目录运行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\repair-dev-port-3000.ps1
```

脚本先检查 3000 是否可用，已可用则不改系统；否则备份端口范围和相关注册表信息到被忽略的 dist-releases，恢复 TCP 动态端口范围到 Windows 默认的 49152–65535，并重启 WinNAT 后实际检查绑定。重启 WinNAT 会短暂影响 WSL/容器网络。脚本不会删除整段保留端口或修改注册表，不会自动重启电脑；若仍无法绑定，会明确报告未修复，保存工作后重启 Windows 再查。备份目录中含原动态端口范围的回退命令。

修复脚本必须输出 `3000 bind OK` 后再运行 `npm run dev`。若重启后复发，保留诊断记录进一步检查系统服务或策略，不要重复改项目端口或把未释放的状态当作修复成功。

前端端口仍支持 FRONTEND_DEV_PORT，但默认值保持 3000。安全检查脚本同样读取该变量，默认输出到 docs/evidence/local-https-check，可通过 EVIDENCE_DIR 指定新目录。先前 dev-port-20261028 的 5173 记录是临时方案验证，不代表恢复 3000 后已经通过验证。
