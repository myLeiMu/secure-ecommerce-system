from django.core.cache import cache
from django.conf import settings
import hashlib
import json
import time


class CacheUtils:
    """缓存工具类"""

    @staticmethod
    def generate_cache_key(prefix, *args, **kwargs):
        """生成缓存键"""
        key_parts = [prefix]

        # 添加位置参数
        for arg in args:
            if arg is not None:
                key_parts.append(str(arg))

        # 添加关键字参数
        for k, v in sorted(kwargs.items()):
            if v is not None:
                key_parts.append(f"{k}={v}")

        key_string = ":".join(key_parts)

        # 如果键太长，使用哈希
        if len(key_string) > 200:
            key_hash = hashlib.md5(key_string.encode()).hexdigest()
            key_string = f"{prefix}:{key_hash}"

        return key_string

    @staticmethod
    def cache_result(key_prefix, expire=300):
        """缓存装饰器"""

        def decorator(func):
            def wrapper(*args, **kwargs):
                # 生成缓存键
                cache_key = CacheUtils.generate_cache_key(key_prefix, *args, **kwargs)

                # 尝试从缓存获取
                result = cache.get(cache_key)

                if result is None:
                    # 缓存未命中，执行函数
                    result = func(*args, **kwargs)
                    # 存储到缓存
                    cache.set(cache_key, result, expire)
                    print(f"[缓存] 缓存未命中，设置缓存: {cache_key}")
                else:
                    print(f"[缓存] 缓存命中: {cache_key}")

                return result

            return wrapper

        return decorator

    @staticmethod
    def invalidate_pattern(pattern):
        """根据模式删除缓存"""
        try:
            from django_redis import get_redis_connection
            redis_conn = get_redis_connection("default")

            keys = redis_conn.keys(f"*{pattern}*")
            if keys:
                redis_conn.delete(*keys)
                print(f"[缓存] 已清除缓存模式: {pattern}, 数量: {len(keys)}")
                return len(keys)
            return 0
        except Exception as e:
            print(f"[缓存错误] 清除缓存失败: {e}")
            return 0

    @staticmethod
    def get_cached_or_set(key, default_func, expire=300, *args, **kwargs):
        """获取缓存或设置默认值"""
        result = cache.get(key)
        if result is None:
            result = default_func(*args, **kwargs)
            cache.set(key, result, expire)
            print(f"[缓存] 设置缓存: {key}")
        else:
            print(f"[缓存] 获取缓存: {key}")
        return result

    @staticmethod
    def delete_key(key):
        """删除指定缓存键"""
        try:
            result = cache.delete(key)
            if result:
                print(f"[缓存] 删除缓存键: {key}")
            return result
        except Exception as e:
            print(f"[缓存错误] 删除缓存键失败: {e}")
            return False


class ProductCache:
    """商品缓存管理"""

    @staticmethod
    @CacheUtils.cache_result("product_list", expire=600)  # 10分钟缓存
    def get_product_list(keyword=None, category_id=None, min_price=None, max_price=None):
        """获取商品列表缓存"""
        from src.unified_service import UnifiedEcommerceService
        service = UnifiedEcommerceService()
        return service.search_products(keyword, category_id, min_price, max_price)

    @staticmethod
    @CacheUtils.cache_result("product_detail", expire=300)  # 5分钟缓存
    def get_product_detail(product_id):
        """获取商品详情缓存"""
        from src.unified_service import UnifiedEcommerceService
        service = UnifiedEcommerceService()
        return service.get_product_detail(product_id)

    @staticmethod
    def invalidate_product_caches(product_id=None):
        """使商品缓存失效"""
        cleared_count = 0

        if product_id:
            # 清除特定商品的缓存
            cleared_count += CacheUtils.invalidate_pattern(f"product_detail:{product_id}")

        # 清除商品列表缓存
        cleared_count += CacheUtils.invalidate_pattern("product_list")

        print(f"[商品缓存] 已清除 {cleared_count} 个缓存")
        return cleared_count


class UserCache:
    """用户缓存管理"""

    @staticmethod
    @CacheUtils.cache_result("user_profile", expire=300)  # 5分钟缓存
    def get_user_profile(username):
        """获取用户信息缓存"""
        from src.unified_service import UnifiedEcommerceService
        service = UnifiedEcommerceService()
        return service.user_system.get_user_info(username)

    @staticmethod
    def invalidate_user_caches(username=None):
        """使用户缓存失效"""
        cleared_count = 0

        if username:
            # 清除特定用户的缓存
            cleared_count += CacheUtils.invalidate_pattern(f"user_profile:{username}")

        print(f"[用户缓存] 已清除 {cleared_count} 个缓存")
        return cleared_count