import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SQLInjectionValidator:
    """SQL注入检测工具"""

    # SQL注入特征模式
    SQL_INJECTION_PATTERNS = [
        # 基础SQL关键字
        r"\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|EXEC|UNION)\b",
        # 注释和终止符
        r"(--|\#|/\*|\*/|;)",
        # 等式注入
        r"(\b(OR|AND)\b\s*\d+\s*=\s*\d+)",
        # 系统函数
        r"(\b(WAITFOR|DELAY|SLEEP|BENCHMARK|PG_SLEEP)\b)",
        # 信息模式
        r"(\b(INFORMATION_SCHEMA|SYSTEM_TABLES|pg_catalog)\b)",
        # 危险字符组合
        r"('(''|[^'])*')",
        r"(\b(XA|START|COMMIT|ROLLBACK)\b)",
    ]

    @classmethod
    def contains_sql_injection(cls, input_string: str) -> bool:
        """检测输入是否包含SQL注入特征"""
        if not input_string or not isinstance(input_string, str):
            return False

        combined_pattern = "|".join(cls.SQL_INJECTION_PATTERNS)

        if re.search(combined_pattern, input_string, re.IGNORECASE):
            logger.warning(f"检测到可能的SQL注入尝试: {input_string}")
            return True

        return False

    @classmethod
    def sanitize_input(cls, input_string: str, max_length: int = 255) -> str:
        """输入清理和验证"""
        if not input_string:
            return ""

        # 移除危险字符
        sanitized = re.sub(r"[;\\\'\"\-\-\#\*/]", "", input_string)

        # 限制长度
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
            logger.warning(f"输入字符串被截断: 原长度{len(input_string)}, 新长度{max_length}")

        return sanitized.strip()

    @classmethod
    def validate_email(cls, email: str) -> bool:
        """邮箱格式验证"""
        if not email:
            return False

        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, email))

    @classmethod
    def validate_phone(cls, phone: str) -> bool:
        """手机号格式验证"""
        if not phone:
            return False

        phone_pattern = r'^1[3-9]\d{9}$'  # 中国大陆手机号
        return bool(re.match(phone_pattern, phone))


class DataMasking:
    """数据脱敏工具"""

    @staticmethod
    def mask_email(email: str) -> str:
        """邮箱脱敏"""
        if not email or "@" not in email:
            return email

        name, domain = email.split("@", 1)
        if len(name) <= 2:
            return f"{name}****@{domain}"
        elif len(name) <= 4:
            return f"{name[:1]}****{name[-1:]}@{domain}"
        else:
            return f"{name[:2]}****{name[-2:]}@{domain}"

    @staticmethod
    def mask_phone(phone: str) -> str:
        """手机号脱敏"""
        if not phone or len(phone) < 7:
            return phone

        return phone[:3] + "****" + phone[-4:]

    @staticmethod
    def mask_card_number(card_number: str) -> str:
        """银行卡号脱敏"""
        if not card_number or len(card_number) < 8:
            return card_number

        return card_number[:6] + "******" + card_number[-4:]

    @staticmethod
    def mask_id_card(id_card: str) -> str:
        """身份证号脱敏"""
        if not id_card or len(id_card) < 8:
            return id_card

        return id_card[:6] + "********" + id_card[-4:]


class InputValidator:
    """输入验证工具"""

    @staticmethod
    def validate_username(username: str) -> tuple[bool, str]:
        """用户名验证"""
        if not username or len(username) < 3:
            return False, "用户名至少3个字符"
        if len(username) > 20:
            return False, "用户名不能超过20个字符"
        if not re.match(r'^[\u4e00-\u9fa5a-zA-Z0-9_]+$', username):
            return False, "用户名只能包含中文、字母、数字和下划线"
        if SQLInjectionValidator.contains_sql_injection(username):
            return False, "用户名包含非法字符"

        return True, "验证通过"

    @staticmethod
    def validate_password(password: str) -> tuple[bool, str]:
        """密码强度验证"""
        if not password or len(password) < 8:
            return False, "密码至少8个字符"
        if len(password) > 20:
            return False, "密码不能超过20个字符"
        if not any(c.isupper() for c in password):
            return False, "密码必须包含大写字母"
        if not any(c.islower() for c in password):
            return False, "密码必须包含小写字母"
        if not any(c.isdigit() for c in password):
            return False, "密码必须包含数字"
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?`~' for c in password):
            return False, "密码必须包含特殊字符"

        return True, "验证通过"

    @staticmethod
    def validate_product_name(name: str) -> tuple[bool, str]:
        """商品名称验证"""
        if not name or len(name) < 2:
            return False, "商品名称至少2个字符"
        if len(name) > 200:
            return False, "商品名称不能超过200个字符"
        if SQLInjectionValidator.contains_sql_injection(name):
            return False, "商品名称包含非法字符"

        return True, "验证通过"