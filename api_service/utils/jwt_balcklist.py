import hashlib
import time
from django.conf import settings
from api_service.utils.redis_client import redis_client


class JWTBlacklist:
    """JWT令牌黑名单管理器"""

    def __init__(self):
        self.prefix = getattr(settings, 'JWT_CONFIG', {}).get('BLACKLIST_PREFIX', 'jwt_blacklist')
        self.token_expire_minutes = getattr(settings, 'JWT_CONFIG', {}).get('ACCESS_TOKEN_EXPIRE_MINUTES', 60)

    def _get_blacklist_key(self, token):
        """生成黑名单键（使用token的MD5哈希）"""
        token_hash = hashlib.md5(token.encode()).hexdigest()
        return f"{self.prefix}:{token_hash}"

    def add_token(self, token, expire_minutes=None):
        """
        将令牌添加到黑名单

        Args:
            token: JWT令牌
            expire_minutes: 过期时间（分钟），None则使用JWT配置的默认过期时间
        """
        if expire_minutes is None:
            expire_minutes = self.token_expire_minutes

        expire_seconds = expire_minutes * 60

        # 存储令牌信息
        blacklist_data = {
            'token_hash': hashlib.md5(token.encode()).hexdigest(),
            'added_at': time.time(),
            'expires_at': time.time() + expire_seconds
        }

        key = self._get_blacklist_key(token)
        success = redis_client.set_key(key, blacklist_data, expire_seconds)

        if success:
            print(f"[JWT黑名单] 令牌已加入黑名单，过期时间: {expire_minutes}分钟")
        else:
            print(f"[JWT黑名单] 令牌加入黑名单失败")

        return success

    def is_blacklisted(self, token):
        """检查令牌是否在黑名单中"""
        key = self._get_blacklist_key(token)
        return redis_client.exists_key(key)

    def remove_token(self, token):
        """从黑名单中移除令牌"""
        key = self._get_blacklist_key(token)
        return redis_client.delete_key(key)

    def cleanup_expired_tokens(self):
        """清理过期的黑名单令牌（Redis会自动处理）"""
        # Redis会自动删除过期的键，这里主要用于手动清理
        try:
            pattern = f"{self.prefix}:*"
            keys = redis_client.keys(pattern)
            cleaned_count = 0

            for key in keys:
                # 检查TTL，如果已经过期但还未被删除，手动删除
                ttl = redis_client.get_ttl(key)
                if ttl == -2:  # 键不存在
                    redis_client.delete_key(key)
                    cleaned_count += 1

            print(f"[JWT黑名单] 清理了 {cleaned_count} 个过期令牌")
            return cleaned_count
        except Exception as e:
            print(f"[JWT黑名单] 清理过期令牌失败: {e}")
            return 0

    def get_blacklist_size(self):
        """获取黑名单大小"""
        try:
            pattern = f"{self.prefix}:*"
            keys = redis_client.keys(pattern)
            return len(keys)
        except Exception as e:
            print(f"[JWT黑名单] 获取黑名单大小失败: {e}")
            return 0

    def get_blacklist_info(self):
        """获取黑名单统计信息"""
        try:
            pattern = f"{self.prefix}:*"
            keys = redis_client.keys(pattern)
            total_size = len(keys)

            # 计算平均剩余时间
            total_ttl = 0
            valid_tokens = 0

            for key in keys:
                ttl = redis_client.get_ttl(key)
                if ttl > 0:
                    total_ttl += ttl
                    valid_tokens += 1

            avg_ttl = total_ttl / valid_tokens if valid_tokens > 0 else 0

            return {
                'total_tokens': total_size,
                'valid_tokens': valid_tokens,
                'avg_ttl_seconds': avg_ttl,
                'avg_ttl_minutes': avg_ttl / 60
            }
        except Exception as e:
            print(f"[JWT黑名单] 获取黑名单信息失败: {e}")
            return {}


# 全局黑名单实例
jwt_blacklist = JWTBlacklist()