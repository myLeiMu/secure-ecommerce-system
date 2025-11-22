import jwt
import datetime
import secrets
import hashlib
import time
import re
from collections import defaultdict
from typing import Optional, Dict, Any
from src.registration import UserSystem
import os

class JWTUtils:
    """JWT工具类"""

    def __init__(self, secret_key: Optional[str] = None, algorithm: str = 'HS256'):
        # 优先使用传入的密钥，其次使用环境变量，最后使用随机密钥
        if secret_key:
            self.secret_key = secret_key
        else:
            env_secret = os.getenv('JWT_SECRET_KEY')
            self.secret_key = env_secret if env_secret else secrets.token_urlsafe(32)
        self.algorithm = algorithm
        print(f"JWT密钥初始化完成，长度: {len(self.secret_key)}")

    def generate_token(self, user_data: Dict[str, Any], expires_in_hours: int = 24) -> str:
        """生成JWT令牌 """
        now = datetime.datetime.now(datetime.timezone.utc)
        expires = now + datetime.timedelta(hours=expires_in_hours)

        payload = {
            'user_id': user_data['user_id'],
            'username': user_data['username'],
            'role': user_data.get('role', 'normal'),
            'iat': int(now.timestamp()),  # 使用整数时间戳
            'exp': int(expires.timestamp()),
            'iss': 'ecommerce-system',
            'jti': secrets.token_urlsafe(16)
        }

        # 确保使用正确的编码方法
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证JWT令牌"""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            print("JWT令牌已过期")
            return None
        except jwt.InvalidTokenError as e:
            print(f"JWT令牌无效: {e}")
            return None
# 认证服务类
class AuthService:
    """认证服务类，集成实验5的防护措施"""

    def __init__(self, user_system, jwt_secret: Optional[str] = None):
        self.user_system = user_system
        self.jwt_utils = JWTUtils(jwt_secret)

        # 登录失败记录（防暴力破解）
        self.failed_attempts = defaultdict(list)
        self.max_attempts = 5
        self.lock_time = 900  # 15分钟锁定

        # 令牌黑名单（用于登出功能）
        self.token_blacklist = set()

    def login(self, username: str, password: str) -> Dict[str, Any]:
        """用户登录认证"""
        # 检查账户是否被锁定
        if self._is_account_locked(username):
            remaining_time = self._get_lock_remaining_time(username)
            return {
                'success': False,
                'message': f'账户已被锁定，请{remaining_time}秒后再试'
            }

        # 调用用户系统的登录验证
        success, msg = self.user_system.login(username, password)

        if success:
            # 登录成功，清除失败记录
            self._clear_login_attempts(username)

            # 获取用户信息生成令牌
            user_info = self.user_system.get_user_info(username)
            if not user_info:
                return {
                    'success': False,
                    'message': '获取用户信息失败'
                }

            user_data = {
                'user_id': user_info['user_id'],
                'username': username,
                'role': user_info.get('user_role', 'normal')  # 改为 user_role
            }

            token = self.jwt_utils.generate_token(user_data)

            return {
                'success': True,
                'message': '登录成功',
                'token': token,
                'user': user_data
            }
        else:
            # 登录失败，记录尝试
            self._record_login_attempt(username)
            remaining_attempts = self.max_attempts - len(self.failed_attempts[username])

            if remaining_attempts <= 0:
                self._lock_account(username)
                return {
                    'success': False,
                    'message': '登录失败次数过多，账户已被锁定15分钟'
                }

            return {
                'success': False,
                'message': f'{msg}，剩余{remaining_attempts}次尝试'
            }

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """完整的令牌验证流程"""
        # 检查黑名单
        if self._is_token_blacklisted(token):
            print("令牌已被撤销")
            return None

        # 基本令牌验证
        payload = self.jwt_utils.verify_token(token)
        if not payload:
            return None

        # 检查用户状态
        username = payload.get('username')
        user_info = self.user_system.get_user_info(username)
        if not user_info:
            print("用户不存在")
            return None

        # 检查用户是否活跃
        if not user_info.get('is_active', True):
            print("用户账户已被禁用")
            return None

        return payload

    def logout(self, token: str) -> bool:
        """用户登出"""
        payload = self.jwt_utils.verify_token(token)
        if payload:
            # 将令牌加入黑名单
            self.token_blacklist.add(token)
            print(f"用户登出: {payload.get('username')}")
            return True
        return False

    def refresh_token(self, old_token: str) -> Optional[str]:
        """刷新JWT令牌"""
        try:
            # 验证旧令牌（即使过期也允许刷新）
            payload = jwt.decode(
                old_token,
                self.jwt_utils.secret_key,
                algorithms=[self.jwt_utils.algorithm],
                options={'verify_exp': False}  # 不验证过期时间
            )

            # 检查令牌是否在黑名单中
            if self._is_token_blacklisted(old_token):
                return None

            # 检查过期时间不能太久（如：7天内）
            exp_time = datetime.datetime.fromtimestamp(payload['exp'], tz=datetime.timezone.utc)
            now = datetime.datetime.now(datetime.timezone.utc)
            if (now - exp_time).days > 7:
                return None

            # 生成新令牌
            user_data = {
                'user_id': payload['user_id'],
                'username': payload['username'],
                'role': payload['role']
            }
            new_token = self.jwt_utils.generate_token(user_data)

            # 将旧令牌加入黑名单
            self.token_blacklist.add(old_token)

            print(f"令牌刷新成功: {payload['username']}")
            return new_token

        except Exception as e:
            print(f"令牌刷新失败: {e}")
            return None

    def _is_account_locked(self, username: str) -> bool:
        """检查账户是否被锁定"""
        if username not in self.failed_attempts:
            return False

        attempts = self.failed_attempts[username]
        if len(attempts) < self.max_attempts:
            return False

        # 检查锁定时间
        first_attempt = attempts[0]
        return time.time() - first_attempt < self.lock_time

    def _get_lock_remaining_time(self, username: str) -> int:
        """获取锁定剩余时间"""
        if username in self.failed_attempts and self.failed_attempts[username]:
            first_attempt = self.failed_attempts[username][0]
            elapsed = time.time() - first_attempt
            return max(0, int(self.lock_time - elapsed))
        return 0

    def _record_login_attempt(self, username: str):
        """记录登录尝试"""
        current_time = time.time()
        attempts = self.failed_attempts[username]

        # 清理过期的尝试记录（超过锁定时间的）
        attempts = [t for t in attempts if current_time - t < self.lock_time]
        attempts.append(current_time)

        self.failed_attempts[username] = attempts

    def _clear_login_attempts(self, username: str):
        """清除登录尝试记录"""
        if username in self.failed_attempts:
            del self.failed_attempts[username]

    def _lock_account(self, username: str):
        """锁定账户"""
        # 这个功能已经在 UserSystem 的 login 方法中实现了
        # 这里保持空实现，避免重复锁定逻辑
        pass

    def _is_token_blacklisted(self, token: str) -> bool:
        """检查令牌是否在黑名单中"""
        return token in self.token_blacklist


# 增强的用户系统
# 在 EnhancedUserSystem 类中添加方法
class EnhancedUserSystem:
    """增强的用户系统，集成认证和会话管理"""

    def __init__(self, user_repository=None, jwt_secret: Optional[str] = None):
        self.user_system = UserSystem(user_repository)
        self.auth_service = AuthService(self.user_system, jwt_secret)  # 传递密钥
    def create_admin_user(self, username: str, password: str, email: str, phone: str):
        """创建管理员用户"""
        return self.user_system.create_admin_user(username, password, email, phone)

    def send_code(self, phone: str):
        """发送验证码"""
        return self.user_system.send_code(phone)

    def register(self, username: str, password: str, phone: str, code: str, email: str = None):
        return self.user_system.register(username, password, phone, code, email)

    def login(self, username: str, password: str):
        return self.auth_service.login(username, password)

    def logout(self, token: str):
        return self.auth_service.logout(token)

    def verify_token(self, token: str):
        return self.auth_service.verify_token(token)

    def refresh_token(self, token: str):
        return self.auth_service.refresh_token(token)

    def get_user_info(self, username: str):
        """获取用户信息"""
        return self.user_system.get_user_info(username)

    def change_password(self, username: str, old_password: str, new_password: str):
        """修改密码"""
        return self.user_system.change_password(username, old_password, new_password)

    def reset_password(self, phone: str, new_password: str, code: str):
        """重置密码"""
        return self.user_system.reset_password(phone, new_password, code)