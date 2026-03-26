### Redis配置（不配也行，系统会直接用内存进行缓存）
在WSL中安装Redis,当然你用虚拟机也可以
```
sudo apt update
sudo apt install redis-server
```

修改配置
`sudo nano /etc/redis/redis.conf`

绑定所有接口，不只是127.0.0.1
`bind 0.0.0.0`

保护模式关闭（允许外部连接）
`protected-mode no`

设置密码（通过查找**# requirepass foobared**这里要去掉#即注释符）
`requirepass Redis_passwd`

这里如果更改了自己的密码也要相应地在.env中更改

设置完成后输入`ip route get 1 | awk '{print $7}'`
查看wsl（或者虚拟机）的ip地址，然后在.env中修改配置

## 后端

先安装项目依赖，在doc里面

先打开Redis
我这里是在wsl中
输入`sudo service redis-server start`或者`sudo systemctl start redis-server`

之后返回主机终端输入
`cd api_service``就可启动后端

### 如果要看swagger文档

访问http://127.0.0.1:8080/api/swagger/

登录账号
normal(这是我们定义的普通用户):
username:testuser
password:TestPass123!
admin:
username:admin
password:AdminPass123!

要认证的功能需要在Authorize中输入**Bearer token(中间有个空格)**
这个token是你登录的时候返回的response里的token
### 手动检测方案（可跳过）
测试黑名单统计
`python manage.py cleanup_jwt_blacklist --stats`

清理过期令牌
`python manage.py cleanup_jwt_blacklist --cleanup`

同时显示统计和清理
`python manage.py cleanup_jwt_blacklist --stats --cleanup`

到此后端配置完毕
## 前端

配置完vue后，在frontend文件夹，即前端项目中输入`npm install`这一步是安装前端的依赖
之后输入`npm run dev`即可，按照终端提示进入前端，也可直接访问 http://localhost:3000/ 
这里前端的管理员和普通用户的界面不一样

## 数据库

我们这里是用的mysql，这里我们是使用的root用户，需要自行在.env中更改你自己的root账户密码，不然连接不上数据库

## mTLS证书弹窗演示（最简）

先在项目根目录执行：
`python -m api_service.tests.prepare_mtls_popup_demo`

它会生成：
- 浏览器导入文件：`keys/mtls_demo/client_testuser.p12`
- nginx配置：`keys/mtls_demo/nginx_mtls_demo.conf`

然后按顺序：
1. 把 `client_testuser.p12` 导入浏览器证书（密码默认 `123456`）
2. 启后端：`conda activate WAF` 后执行 `python api_service\manage.py runserver 127.0.0.1:8080`
3. 启nginx（指定上面生成的配置文件）
4. 打开 `https://localhost:8443/api/health/`，会弹证书选择窗口
5. 调用 `https://localhost:8443/api/auth/cert/mtls-login`，body:
`{"username":"testuser"}`
