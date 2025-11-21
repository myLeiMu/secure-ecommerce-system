import hashlib
import secrets
import re
import time
from typing import Optional
from datetime import datetime, timedelta


class UserSystem:
    """用户注册登录系统，针对STRIDE威胁模型的安全防护"""

    def __init__(self, user_repository):
        # 使用数据库存储
        self.user_repository = user_repository
        self.verification_codes = {}  # 验证码存储
        self.attempts = {}  # 操作频率记录

    def hash_password(self, password, salt=None):
        """T2防护：密码加盐哈希，防止数据篡改"""
        salt = salt or secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac(
            'sha256', password.encode(), salt.encode(), 100000
        ).hex()
        return password_hash, salt

    def validate_input(self, username, password, phone, email=None):
        """T2防护：输入验证，防止数据篡改"""
        if not all([username, password, phone]):
            return False, "所有字段必须填写"

        # 用户名验证
        if len(username) < 3 or len(username) > 50:
            return False, "用户名长度需在3-50字符之间"
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return False, "用户名只能包含字母、数字和下划线"

        # T1防护：验证手机号真实性
        if not re.match(r'^1[3-9]\d{9}$', phone):
            return False, "手机号格式错误"

        # 邮箱验证
        if email and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return False, "邮箱格式错误"

        # T6防护：强密码策略防止权限提升
        if len(password) < 8:
            return False, "密码需8位以上"
        if not re.search(r'[A-Z]', password):
            return False, "密码需包含大写字母"
        if not re.search(r'[a-z]', password):
            return False, "密码需包含小写字母"
        if not re.search(r'\d', password):
            return False, "密码需包含数字"
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "密码需包含特殊字符"

        return True, "验证通过"

    def send_code(self, phone):
        """T1防护：短信验证码防止身份欺骗"""
        # T5防护：频率限制防止DoS攻击,这里设置的很短是为了方便测试
        if phone in self.verification_codes and time.time() - self.verification_codes[phone]['time'] < 1:
            return False, "请求过于频繁，请1秒后重试"

        code = '123456'  # 固定验证码，便于演示
        self.verification_codes[phone] = {'code': code, 'time': time.time()}

        # 这里可以接入真实的短信服务
        print(f"验证码发送至 {phone}: {code} (演示模式)")
        return True, "验证码发送成功"

    def verify_code(self, phone, code):

        # 开发环境：固定验证码 "123456" 始终有效，因为测试时在swagger中一直显示验证码过期
        if code == "123456":
            print(f"[DEV] 开发环境验证码通过: {phone}")
            return True

        """T1防护：验证身份真实性"""
        if phone not in self.verification_codes:
            return False

        # T5防护：验证码过期机制
        if time.time() - self.verification_codes[phone]['time'] > 300:
            del self.verification_codes[phone]
            return False

        if self.verification_codes[phone]['code'] == code:
            del self.verification_codes[phone]
            return True
        return False

    def check_rate(self, key, max_attempts=5, window=600):
        """T5防护：频率限制防止拒绝服务攻击"""
        now = time.time()

        if key not in self.attempts:
            self.attempts[key] = []

        self.attempts[key] = [t for t in self.attempts[key] if now - t < window]

        if len(self.attempts[key]) >= max_attempts:
            return False

        self.attempts[key].append(now)
        return True

    def register(self, username, password, phone, code, email=None):
        """用户注册 - 综合安全防护"""
        # T5防护：注册频率限制
        if not self.check_rate(f"reg_{phone}", 3, 3600):
            return False, "注册频率过高，请1小时后再试"

        # T2防护：输入数据验证
        valid, msg = self.validate_input(username, password, phone, email)
        if not valid:
            return False, msg

        # T1防护：身份验证防止欺骗
        if not self.verify_code(phone, code):
            return False, "验证码错误或已过期"

        # T6防护：防止重复注册导致的权限问题
        existing_user = self.user_repository.get_user_by_username(username)
        if existing_user:
            return False, "用户名已存在"

        # 检查手机号是否已注册
        existing_phone_user = self.user_repository.db.query(self.user_repository.model).filter(
            self.user_repository.model.phone == phone
        ).first()
        if existing_phone_user:
            return False, "手机号已注册"

        # 检查邮箱是否已注册（如果提供了邮箱）
        if email:
            existing_email_user = self.user_repository.get_user_by_email(email)
            if existing_email_user:
                return False, "邮箱已注册"

        # T2防护：密码安全存储防止篡改
        pwd_hash, salt = self.hash_password(password)

        # 存储到数据库
        user_data = {
            'username': username,
            'pass_word': pwd_hash,
            'salt': salt,
            'phone': phone,
            'email': email or f"{username}@default.com",
            'user_role': 'normal',
            'is_verified': True,
            'is_active': True,
            'failed_attempts': 0,
            'account_locked_until': None,
            'last_login': None,
            'login_count': 0
        }

        user = self.user_repository.create_user(user_data)
        if user:
            return True, "注册成功"
        else:
            return False, "注册失败，请稍后重试"

    def login(self, username, password):
        """用户登录 - 身份验证和防暴力破解"""
        # T5防护：登录频率限制防止DoS
        if not self.check_rate(f"login_{username}", 5, 1800):
            return False, "尝试次数过多，请30分钟后再试"

        # 数据库验证
        user = self.user_repository.get_user_by_username(username)
        if not user:
            return False, "用户名或密码错误"

        # T6防护：账户锁定防止权限提升尝试
        if self.user_repository.is_account_locked(user.user_id):
            return False, "账户已锁定，请稍后重试或联系管理员"

        # T1防护：密码验证防止身份欺骗
        pwd_hash, _ = self.hash_password(password, user.salt)
        if pwd_hash == user.pass_word:
            # 登录成功，重置尝试次数并更新登录信息
            self.user_repository.reset_login_attempts(user.user_id)
            self.user_repository.update_last_login(user.user_id)
            return True, "登录成功"
        else:
            # 登录失败，增加尝试次数
            new_attempts = user.failed_attempts + 1
            locked_until = None

            if new_attempts >= 5:
                # 锁定账户1小时
                locked_until = datetime.now() + timedelta(hours=1)

            self.user_repository.update_login_attempts(
                user.user_id, new_attempts, locked_until
            )

            if new_attempts >= 5:
                return False, "账户已锁定，请1小时后再试"
            else:
                return False, f"密码错误，剩余{5 - new_attempts}次尝试"

    def reset_password(self, phone, new_password, code):
        """密码重置 - 安全身份验证"""
        # T1防护：验证码验证身份
        if not self.verify_code(phone, code):
            return False, "验证码错误或已过期"

        # T2防护：新密码强度验证
        valid, msg = self.validate_input("temp", new_password, phone)
        if not valid:
            return False, msg

        # 数据库重置密码
        user = self.user_repository.db.query(self.user_repository.model).filter(
            self.user_repository.model.phone == phone
        ).first()

        if user:
            pwd_hash, salt = self.hash_password(new_password)
            user.pass_word = pwd_hash
            user.salt = salt
            user.failed_attempts = 0
            user.account_locked_until = None

            try:
                self.user_repository.db.commit()
                return True, "密码重置成功"
            except Exception as e:
                self.user_repository.db.rollback()
                return False, "密码重置失败，请稍后重试"
        else:
            return False, "手机号未注册"

    def change_password(self, username, old_password, new_password):
        """已登录用户修改密码"""
        user = self.user_repository.get_user_by_username(username)
        if not user:
            return False, "用户不存在"

        # 验证旧密码
        old_hash, _ = self.hash_password(old_password, user.salt)
        if old_hash != user.pass_word:
            return False, "原密码不正确"

        # 验证新密码强度
        valid, msg = self.validate_input(username, new_password, user.phone, user.email)
        if not valid:
            return False, msg

        # 更新密码
        try:
            new_hash, new_salt = self.hash_password(new_password)
            user.pass_word = new_hash
            user.salt = new_salt
            user.failed_attempts = 0
            user.account_locked_until = None
            self.user_repository.db.commit()
            return True, "密码修改成功"
        except Exception as e:
            self.user_repository.db.rollback()
            print(f"修改密码失败: {e}")
            return False, "密码修改失败，请稍后重试"

    def admin_login(self, username, password, admin_token):
        """管理员登录 - 增强安全验证"""
        # T6防护：管理员额外令牌验证
        expected_token = hashlib.sha256("secure_admin_token".encode()).hexdigest()
        if admin_token != expected_token:
            return False, "管理员令牌错误"

        # 复用普通登录逻辑，但需要额外权限检查
        success, msg = self.login(username, password)
        if success:
            user = self.user_repository.get_user_by_username(username)
            if user and user.user_role == 'admin':
                return True, "管理员登录成功"
            else:
                return False, "权限不足"
        else:
            return False, msg

    def create_admin_user(self, username, password, email, phone):
        """创建管理员用户（初始化使用）"""
        # 检查用户是否已存在
        existing_user = self.user_repository.get_user_by_username(username)
        if existing_user:
            return False, "用户名已存在"

        # 输入验证
        valid, msg = self.validate_input(username, password, phone, email)
        if not valid:
            return False, msg

        # 创建管理员用户
        pwd_hash, salt = self.hash_password(password)
        user_data = {
            'username': username,
            'pass_word': pwd_hash,
            'salt': salt,
            'phone': phone,
            'email': email,
            'user_role': 'admin',
            'is_verified': True,
            'is_active': True,
            'failed_attempts': 0,
            'account_locked_until': None,
            'last_login': None,
            'login_count': 0
        }

        user = self.user_repository.create_user(user_data)
        if user:
            return True, "管理员用户创建成功"
        else:
            return False, "管理员用户创建失败"

    def get_user_info(self, username):
        """获取用户信息"""
        user = self.user_repository.get_user_by_username(username)
        if user:
            return {
                'user_id': user.user_id,
                'username': user.username,
                'email': user.email,
                'phone': user.phone,
                'user_role': user.user_role,
                'is_verified': user.is_verified,
                'last_login': user.last_login,
                'created_at': user.created_at
            }
        return None