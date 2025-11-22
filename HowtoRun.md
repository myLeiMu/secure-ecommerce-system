## 后端
先安装项目依赖，在doc里面

### redis配置
在WSL中安装Redis
sudo apt update
sudo apt install redis-server
修改配置
sudo nano /etc/redis/redis.conf

绑定所有接口，不只是127.0.0.1
bind 0.0.0.0

保护模式关闭（允许外部连接）
protected-mode no

设置密码（通过查找# requirepass foobared这里要去掉#即注释符）
requirepass Redis_passwd

设置完成后输入ip route get 1 | awk '{print $7}'
查看wsl的ip地址，然后在.env中修改配置

### 如果要看swagger
先打开redis
我这里是在wsl中
输入sudo service redis-server start或者sudo systemctl start redis-server

终端输入
cd api_service
python manage.py runserver 0.0.0.0:8080

访问http://127.0.0.1:8080/api/swagger/

登录账号
normal:
username:testuser
password:TestPass123!
admin:
username:admin
password:AdminPass123!

要认证的功能需要在Authorize中输入Bearer token（中间有个空格
### 手动检测方案（可跳过）
测试黑名单统计
python manage.py cleanup_jwt_blacklist --stats

清理过期令牌
python manage.py cleanup_jwt_blacklist --cleanup

同时显示统计和清理
python manage.py cleanup_jwt_blacklist --stats --cleanup

到此后端配置完毕
## 前端

前端采用的vue，需要配置环境，自行搜索教程

配置完vue后，在frontend文件夹，即前端项目中输入npm install
之后输入npm run dev即可，按照终端提示进入前端
这里前端的管理员和普通用户的界面不一样