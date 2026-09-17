# 第2周课堂实践实测记录

环境：隔离 SQLite、临时 SM2 CA、真实证书签名校验、Django 集成接口。业务角色 normal、admin、auditor。

| 检查项 | 接口 | 预期 | 实际 | 结果 |
| --- | --- | --- | --- | --- |
| certificate challenge | POST /api/auth/cert/challenge | 200 | 200 | 通过 |
| SM2 signature rejected | POST /api/auth/cert/login | 401 | 401 | 通过 |
| certificate challenge | POST /api/auth/cert/challenge | 200 | 200 | 通过 |
| user1 certificate login | POST /api/auth/cert/login | 200 | 200 | 通过 |
| trader denied platform management | GET /api/admin/users | 403 | 403 | 通过 |
| trader denied audit | GET /api/audit/events | 403 | 403 | 通过 |
| trader own order allowed | GET /api/orders/1 | 200 | 200 | 通过 |
| trader own listings allowed | GET /api/merchant/products | 200 | 200 | 通过 |
| trader cannot edit another seller listing | PUT /api/merchant/products/1 | 403 | 403 | 通过 |
| certificate challenge | POST /api/auth/cert/challenge | 200 | 200 | 通过 |
| user4 certificate login | POST /api/auth/cert/login | 200 | 200 | 通过 |
| certificate alone issues no privileged JWT |   | 断言成立 | 断言成立 | 通过 |
| MFA alone without challenge denied | POST /api/auth/mfa/verify | 400 | 400 | 通过 |
| incorrect MFA denied | POST /api/auth/mfa/verify | 400 | 400 | 通过 |
| correct MFA allows login | POST /api/auth/mfa/verify | 200 | 200 | 通过 |
| consumed challenge replay denied | POST /api/auth/mfa/verify | 400 | 400 | 通过 |
| auditor audit allowed | GET /api/audit/events | 200 | 200 | 通过 |
| auditor platform management denied | GET /api/admin/users | 403 | 403 | 通过 |
| auditor order creation denied | POST /api/orders | 403 | 403 | 通过 |
| auditor listing management denied | GET /api/merchant/products | 403 | 403 | 通过 |
| certificate challenge | POST /api/auth/cert/challenge | 200 | 200 | 通过 |
| user4 certificate login | POST /api/auth/cert/login | 200 | 200 | 通过 |
| old TOTP in new challenge denied | POST /api/auth/mfa/verify | 400 | 400 | 通过 |
| one-time recovery allows login | POST /api/auth/mfa/verify | 200 | 200 | 通过 |
| certificate challenge | POST /api/auth/cert/challenge | 200 | 200 | 通过 |
| user4 certificate login | POST /api/auth/cert/login | 200 | 200 | 通过 |
| used recovery rejected | POST /api/auth/mfa/verify | 400 | 400 | 通过 |
| required MFA audit events recorded |   | 断言成立 | 断言成立 | 通过 |

证书签名验证未被模拟。页面截图由独立演示管理员登录后读取同一隔离数据库生成。原 MySQL 数据和角色未修改。

后端原有 12 项回归测试亦已通过；本文件记录本次运行结果，重新运行脚本会更新 results.json。