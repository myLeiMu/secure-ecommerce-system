"""Correctness gates for performance changes; no timing thresholds in unit tests."""
import hashlib
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor

from api_service.tests import test_course_security as course
from src.utils import security


class SM3CompatibilityTests(unittest.TestCase):
    def test_standard_digest_and_independent_thread_state(self):
        expected = '66c7f0f462eeedd9d1f2d46bdc10e4e24167c4875cf2f7a2297da02b8f4ba8e0'
        self.assertEqual(security.sm3_hexdigest(b'abc'), expected)
        data = [bytes([i])*127 for i in range(20)]
        with ThreadPoolExecutor(max_workers=4) as pool:
            actual = list(pool.map(security.sm3_digest, data))
        self.assertEqual(actual, [hashlib.new('sm3', item).digest() for item in data])

    def test_native_and_python_preserve_password_hashes_and_hmac(self):
        for password, salt, rounds, length in [(b'password',b'salt',1,32),
                ('密码Test123!'.encode(),b'\x00\xffsalt',3,65),
                (b'x'*100,b'salt',2,48),(b'Week9PerfOnly123!',bytes.fromhex('11'*16),2500,32)]:
            with self.subTest(rounds=rounds,length=length):
                expected = hashlib.pbkdf2_hmac('sm3',password,salt,rounds,length)
                self.assertEqual(security.pbkdf2_sm3(password,salt,rounds,length),expected)
                with patch.object(security,'_NATIVE_SM3',False):
                    self.assertEqual(security.pbkdf2_sm3(password,salt,rounds,length),expected)
        import hmac
        for key in (b'a',b'x'*100):
            expected = hmac.digest(key,b'JWT-header.payload','sm3')
            self.assertEqual(security.hmac_sm3(key,b'JWT-header.payload'),expected)
            with patch.object(security,'_NATIVE_SM3',False):
                self.assertEqual(security.hmac_sm3(key,b'JWT-header.payload'),expected)

    def test_invalid_kdf_cost_is_rejected(self):
        for rounds, length in ((0,32),(-1,32),(1,0),(1,-1)):
            with self.assertRaises(ValueError): security.pbkdf2_sm3(b'p',b's',rounds,length)


class Week9LifecycleTests(unittest.TestCase):
    setUp = course.CourseSecurityTests.setUp
    token = course.CourseSecurityTests.token
    request = course.CourseSecurityTests.request

    def tearDown(self):
        from django.core.cache import cache
        cache.clear()

    def test_request_service_does_not_run_ddl_seed_or_generate_keys(self):
        from src.unified_service import UnifiedEcommerceService
        with (patch.object(UnifiedEcommerceService,'_initialize_database',side_effect=AssertionError('DDL in request')),
              patch.object(UnifiedEcommerceService,'_create_sample_data',side_effect=AssertionError('Seeding in request'))):
            with UnifiedEcommerceService() as service:
                self.assertIsNone(service._asymmetric_service)

    def test_request_scope_closes_sessions_even_on_exception(self):
        from src.Data_base.database import request_session_scope
        from src.unified_service import UnifiedEcommerceService
        from sqlalchemy import text
        baseline = course.engine.pool.checkedout()
        held = []
        with self.assertRaises(RuntimeError):
            with request_session_scope():
                service = UnifiedEcommerceService()
                held.append(service)  # Keep it alive to prove closure is not garbage collection.
                service.db_session.execute(text('SELECT 1')).scalar_one()
                self.assertGreater(course.engine.pool.checkedout(),baseline)
                raise RuntimeError('view failed')
        self.assertEqual(course.engine.pool.checkedout(),baseline)

    def test_hot_catalog_hit_and_invalidation_leave_other_state_intact(self):
        from api_service.utils.cache_utils import ProductCache
        from django.core.cache import cache
        from sqlalchemy import event
        cache.clear()
        cache.set('unrelated_mfa_state','keep',300)
        statements = []
        def record(*args): statements.append(args[2])
        event.listen(course.engine,'before_cursor_execute',record)
        try:
            first = ProductCache.get_product_list(category_id=1)
            count = len(statements)
            self.assertEqual(ProductCache.get_product_list(category_id=1),first)
            self.assertEqual(len(statements),count)
            with course.SessionLocal.begin() as db: db.get(course.Product,1).stock_quantity=0
            ProductCache.invalidate_product_caches(1)
            self.assertEqual(ProductCache.get_product_list(category_id=1),[])
            self.assertEqual(cache.get('unrelated_mfa_state'),'keep')
            self.assertTrue(all(isinstance(item,dict) for item in first))
        finally:
            event.remove(course.engine,'before_cursor_execute',record)

    def test_inflight_old_generation_cannot_repopulate_new_cache(self):
        from api_service.utils.cache_utils import ProductCache
        from django.core.cache import cache
        cache.clear()
        def old_loader():
            ProductCache.invalidate_product_caches(1)
            return {'stock':1}
        ProductCache._cached('race',old_loader)
        self.assertEqual(ProductCache._cached('race',lambda:{'stock':0}),{'stock':0})

    def test_cache_outage_falls_back_to_database(self):
        from api_service.utils.cache_utils import ProductCache
        with patch('api_service.utils.cache_utils.cache.get',side_effect=ConnectionError):
            self.assertEqual(ProductCache.get_product_list(category_id=1)[0]['product_id'],1)

    def test_successful_order_invalidates_hot_detail_and_catalog(self):
        from api_service.utils.cache_utils import ProductCache
        from django.core.cache import cache
        cache.clear()
        with course.SessionLocal.begin() as db: db.get(course.Product,1).stock_quantity=1
        self.assertEqual(ProductCache.get_product_detail(1)['stock_quantity'],1)
        self.assertEqual(len(ProductCache.get_product_list(category_id=1)),1)
        self.assertEqual(self.request('/api/cart',{'product_id':1,'quantity':1},uid=1)[0],200)
        self.assertEqual(self.request('/api/orders',{},uid=1)[0],200)
        self.assertEqual(ProductCache.get_product_detail(1)['stock_quantity'],0)
        self.assertEqual(ProductCache.get_product_list(category_id=1),[])
