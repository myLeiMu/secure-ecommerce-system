import redis
import json
import time
from django.conf import settings


class RedisClient:
    def __init__(self):
        self.redis_config = getattr(settings, 'REDIS_CONFIG', {})
        self.connection = None
        self._fallback_cache = {}  # 内存缓存作为备选
        self._initialize_connection()

    def _initialize_connection(self):
        """初始化Redis连接，失败时使用内存缓存"""
        try:
            host = self.redis_config.get('HOST', 'localhost')
            port = self.redis_config.get('PORT', 6379)
            db = self.redis_config.get('DB', 0)
            password = self.redis_config.get('PASSWORD')

            # 移除SSL参数，使用标准的连接参数
            connection_pool = redis.ConnectionPool(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
                retry_on_timeout=True,
                max_connections=10
            )
            self.connection = redis.Redis(connection_pool=connection_pool)

            # 测试连接
            self.connection.ping()
            print(f"Redis连接成功！主机: {host}:{port}, 数据库: {db}")

        except Exception as e:
            print(f"Redis连接失败: {e}，将使用内存缓存")
            self.connection = None

    def set_key(self, key, value, expire=None):
        """设置键值对"""
        try:
            if self.connection:
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False)
                result = self.connection.set(key, value, ex=expire)
                return result is not None
            else:
                # 使用内存缓存
                self._fallback_cache[key] = {
                    'value': value,
                    'expire_time': None if not expire else time.time() + expire
                }
                return True
        except Exception as e:
            print(f"Redis设置键失败: {e}")
            return False

    def get_key(self, key):
        """获取键值"""
        try:
            if self.connection:
                value = self.connection.get(key)
                if value:
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        return value
                return None
            else:
                # 从内存缓存获取
                if key in self._fallback_cache:
                    cache_item = self._fallback_cache[key]
                    # 检查是否过期
                    if cache_item['expire_time'] and time.time() > cache_item['expire_time']:
                        del self._fallback_cache[key]
                        return None
                    return cache_item['value']
                return None
        except Exception as e:
            print(f"Redis获取键失败: {e}")
            return None

    def exists_key(self, key):
        """检查键是否存在"""
        try:
            if self.connection:
                return self.connection.exists(key) > 0
            else:
                return key in self._fallback_cache
        except Exception as e:
            print(f"Redis检查键失败: {e}")
            return False

    def delete_key(self, key):
        """删除键"""
        try:
            if self.connection:
                return self.connection.delete(key) > 0
            else:
                if key in self._fallback_cache:
                    del self._fallback_cache[key]
                    return True
                return False
        except Exception as e:
            print(f"Redis删除键失败: {e}")
            return False

    def set_expire(self, key, expire):
        """设置键的过期时间"""
        try:
            if self.connection:
                return self.connection.expire(key, expire)
            return False
        except Exception as e:
            print(f"Redis设置过期时间失败: {e}")
            return False

    def get_ttl(self, key):
        """获取键的剩余生存时间"""
        try:
            if self.connection:
                return self.connection.ttl(key)
            return -2
        except Exception as e:
            print(f"Redis获取TTL失败: {e}")
            return -2

    def keys(self, pattern):
        """根据模式查找键"""
        try:
            if self.connection:
                return self.connection.keys(pattern)
            return []
        except Exception as e:
            print(f"Redis查找键失败: {e}")
            return []

    def ping(self):
        """测试连接"""
        try:
            if self.connection:
                return self.connection.ping()
            return False
        except Exception as e:
            print(f"Redis Ping失败: {e}")
            return False


# 全局Redis客户端实例
redis_client = RedisClient()