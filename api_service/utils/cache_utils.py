from django.core.cache import cache
from django.conf import settings
import json
import time
from src.utils.security import sm3_hexdigest


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
            key_hash = sm3_hexdigest(key_string.encode("utf-8"))
            key_string = f"{prefix}:{key_hash}"

        return key_string

    @staticmethod
    def cache_result(key_prefix, expire=300):
        """缓存装饰器"""

        def decorator(func):
            def wrapper(*args, **kwargs):
                # 生成缓存键
                cache_key = CacheUtils.generate_cache_key(key_prefix, *args, **kwargs)
                try:
                    # 尝试从缓存获取
                    result = cache.get(cache_key)
                    if result is None:
                        result = func(*args, **kwargs)
                        cache.set(cache_key, result, expire)
                        print(f"[缓存] 缓存未命中，设置缓存: {cache_key}")
                    else:
                        print(f"[缓存] 缓存命中: {cache_key}")
                    return result
                except Exception as e:
                    print(f"[缓存错误] 读取缓存失败，降级直连: {e}")
                    return func(*args, **kwargs)

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
            # Redis 不可用时回退到本地缓存，无法按 pattern 删除，直接清空避免脏读
            try:
                cache.clear()
                print("[缓存] Redis不可用，已执行本地缓存清空")
                return 1
            except Exception as clear_error:
                print(f"[缓存错误] 本地缓存清空失败: {clear_error}")
                return 0

    @staticmethod
    def get_cached_or_set(key, default_func, expire=300, *args, **kwargs):
        """获取缓存或设置默认值"""
        try:
            result = cache.get(key)
            if result is None:
                result = default_func(*args, **kwargs)
                cache.set(key, result, expire)
                print(f"[缓存] 设置缓存: {key}")
            else:
                print(f"[缓存] 获取缓存: {key}")
            return result
        except Exception as e:
            print(f"[缓存错误] 缓存不可用，降级直连: {e}")
            return default_func(*args, **kwargs)

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
    """Bounded DTO caches with generation-based invalidation, no Redis KEYS."""
    GENERATION_KEY = 'product_catalog_generation_v2'

    @staticmethod
    def _generation():
        import secrets
        generation = cache.get(ProductCache.GENERATION_KEY)
        if generation is None:
            candidate = secrets.token_hex(16)
            cache.add(ProductCache.GENERATION_KEY, candidate, timeout=None)
            generation = cache.get(ProductCache.GENERATION_KEY)
        if not generation:
            raise RuntimeError('Product cache generation unavailable')
        return generation

    @staticmethod
    def _cached(kind, loader, **parameters):
        try:
            generation = ProductCache._generation()
            key = CacheUtils.generate_cache_key('product_v2', generation, kind, **parameters)
            value = cache.get(key)
            if value is not None:
                return value
        except Exception:
            return loader()  # A cache outage must never turn into a fake empty catalog.
        value = loader()
        try:
            cache.set(key, value, 300)
        except Exception:
            pass
        # If invalidation happened during the SELECT, this value is written only
        # under the old generation, unreachable by subsequent requests.
        return value

    @staticmethod
    def get_product_list(keyword=None, category_id=None, min_price=None, max_price=None):
        def load():
            from src.Data_base.database import SessionLocal
            from src.Data_base.repositories.product_repository import ProductRepository
            with SessionLocal() as db:
                products = ProductRepository(db).search_products_safe(keyword, category_id, min_price, max_price)
                return [{'product_id':p.product_id, 'sku':p.sku, 'product_name':p.product_name,
                         'description':p.description or '', 'sale_price':float(p.sale_price),
                         'stock_quantity':p.stock_quantity, 'image_urls':p.image_urls or [],
                         'category_id':p.category_id, 'seller_id':p.seller_id,
                         'is_available':bool(p.is_available), 'created_at':p.created_at,
                         'updated_at':p.updated_at} for p in products]
        return ProductCache._cached('list', load, keyword=keyword, category_id=category_id,
                                    min_price=min_price, max_price=max_price)

    @staticmethod
    def get_product_detail(product_id):
        def load():
            from src.unified_service import UnifiedEcommerceService
            with UnifiedEcommerceService() as service:
                product = service.get_product_detail(product_id)
                if product is None:
                    return None
                return {'product_id':product.product_id, 'product_name':product.product_name,
                        'description':product.description or '', 'sale_price':float(product.sale_price),
                        'stock_quantity':product.stock_quantity, 'image_urls':product.image_urls or [],
                        'category_id':product.category_id, 'category_name':product.category.category_name if product.category else '',
                        'seller_id':product.seller_id, 'sku':product.sku,
                        'created_at':product.created_at, 'updated_at':product.updated_at}
        return ProductCache._cached('detail', load, product_id=product_id)

    @staticmethod
    def invalidate_product_caches(product_id=None):
        import secrets
        # Changes to stock, seller status, prices or categories affect list and
        # detail responses. Rotate the namespace after commit; do not flush MFA,
        # token, or other application caches. Old keys expire within five minutes.
        try:
            cache.set(ProductCache.GENERATION_KEY, secrets.token_hex(16), timeout=None)
            return 1
        except Exception:
            # If cache is unavailable, subsequent reads use the database.
            return 0


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
