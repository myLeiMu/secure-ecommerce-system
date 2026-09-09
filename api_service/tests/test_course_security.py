"""Run: python -m unittest api_service.tests.test_course_security -v"""
import json
import os
import secrets
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from cryptography.fernet import Fernet

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['DJANGO_SETTINGS_MODULE'] = 'service.test_settings'
os.environ['DATABASE_URL'] = 'sqlite:///file:course_' + secrets.token_hex(8) + '?mode=memory&cache=shared&uri=true'
os.environ['JWT_SECRET_KEY'] = 'test-only-key-' + 'x' * 48
os.environ['MFA_ENCRYPTION_KEY'] = Fernet.generate_key().decode()
os.environ['SM3_PBKDF2_ITERATIONS'] = '50'  # Fast fixtures; production setting is untouched.
import django
django.setup()
from django.test import Client, RequestFactory
from sqlalchemy import BigInteger
from sqlalchemy.ext.compiler import compiles
from src.Data_base.database import Base, engine, SessionLocal
from src.Data_base.models.user import User
from src.Data_base.models.product import Product, Category
from src.Data_base.models.order import Order, OrderStatus, PaymentStatus
from src.Data_base.models.security import AuditEvent, SecurityState
from api_service.api.security_core import (cipher, totp, verify_factor, state_for, begin_login, login_data, digest)


@compiles(BigInteger, 'sqlite')
def sqlite_bigint(type_, compiler, **kw):
    return 'INTEGER'


class CourseSecurityTests(unittest.TestCase):
    def setUp(self):
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        self.client = Client()
        for method in ('_initialize_database', '_create_sample_data'):
            mock = patch('src.unified_service.UnifiedEcommerceService.' + method)
            mock.start()
            self.addCleanup(mock.stop)
        from src.registration import UserSystem
        password_hash, salt = UserSystem(None).hash_password('TestPass123!')
        with SessionLocal.begin() as db:
            for uid, role in enumerate(('normal', 'merchant', 'admin', 'auditor', 'merchant'), 1):
                db.add(User(user_id=uid, username=f'user{uid}', email=f'u{uid}@example.com',
                            phone=f'1380000000{uid}', pass_word=password_hash, salt=salt,
                            user_role=role, is_active=True, is_verified=True))
            db.add(Category(category_id=1, category_name='Test'))
            db.add(Product(product_id=1, sku='p1', product_name='Product', sale_price=10,
                           stock_quantity=5, category_id=1, seller_id=2, is_active=True, status='active'))
            db.add(Order(order_id=1, order_number='test-order', user_id=1, subtotal_amount=10,
                         total_amount=10, payment_status=PaymentStatus.PAID, order_status=OrderStatus.PENDING))

    def token(self, uid, mfa=True):
        with SessionLocal.begin() as db:
            state = state_for(db, uid)
            state.enabled = mfa
            return login_data(db.get(User, uid), state, mfa=mfa)['token']


    def request(self, path, body=None, uid=None, method='POST', token=None):
        headers = {'HTTP_AUTHORIZATION': 'Bearer ' + (token or self.token(uid))} if uid or token else {}
        response = self.client.generic(method, path, json.dumps(body or {}), content_type='application/json', **headers)
        return response.status_code, response.json()


    def test_totp_rfc6238_replay_skew_lock_and_recovery(self):
        secret = 'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ'
        self.assertEqual(totp(secret, 59 // 30), '287082')
        state = SecurityState(enabled=True, secret=cipher().encrypt(secret.encode()).decode(), last_step=-1,
                              failures=0, locked_until=0, recovery_hashes=json.dumps([digest('recovery')]))
        self.assertTrue(verify_factor(state, '287082', now=59))
        self.assertFalse(verify_factor(state, '287082', now=59))
        self.assertTrue(verify_factor(state, totp(secret, 3), now=60))
        self.assertTrue(verify_factor(state, 'recovery', now=60))
        self.assertFalse(verify_factor(state, 'recovery', now=60))
        for _ in range(5):
            verify_factor(state, 'bad', now=60)
        self.assertGreater(state.locked_until, 60)
        self.assertFalse(verify_factor(state, totp(secret, 4), now=120))


    def test_login_requires_mfa_and_enrollment_returns_one_time_codes(self):
        status, response = self.request('/api/auth/login', {'username': 'user3', 'password': 'TestPass123!'})
        self.assertEqual(status, 200, response)
        data = response['data']
        self.assertTrue(data['mfa_required'])
        self.assertNotIn('token', data)
        body = {'challenge': data['challenge'], 'code': totp(data['secret'], int(time.time()) // 30)}
        status, response = self.request('/api/auth/mfa/verify', body)
        self.assertEqual(status, 200, response)
        self.assertEqual(len(response['data']['recovery_codes']), 8)
        self.assertEqual(self.request('/api/auth/mfa/verify', body)[0], 400)

    def test_role_guards_auditor_scope_and_stale_session(self):
        for uid in (1, 2, 4):
            response = self.client.get('/api/admin/users', HTTP_AUTHORIZATION='Bearer ' + self.token(uid))
            self.assertEqual(response.status_code, 403)
        old_token = self.token(3, mfa=False)
        self.assertEqual(self.client.get('/api/admin/users', HTTP_AUTHORIZATION='Bearer ' + old_token).status_code, 401)
        response = self.client.get('/api/audit/events', HTTP_AUTHORIZATION='Bearer ' + self.token(4))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get('/api/orders', HTTP_AUTHORIZATION='Bearer ' + self.token(4)).status_code, 403)
        token = self.token(2)
        self.assertEqual(self.request('/api/admin/users/2', {'role': 'normal'}, uid=3, method='PATCH')[0], 200)
        self.assertEqual(self.client.get('/api/merchant/products', HTTP_AUTHORIZATION='Bearer ' + token).status_code, 401)

    def test_trading_user_can_publish_only_manage_own_products(self):
        payload = {'sku': 'used-book', 'product_name': '二手教材', 'sale_price': '12.00',
                   'stock_quantity': 1, 'category_id': 1, 'seller_id': 2}
        self.assertEqual(self.request('/api/merchant/products', payload, uid=1)[0], 200)
        with SessionLocal() as db:
            product = db.query(Product).filter_by(sku='used-book').one()
            product_id = product.product_id
            self.assertEqual(product.seller_id, 1)
        status, response = self.request('/api/merchant/products', uid=1, method='GET')
        self.assertEqual(status, 200)
        self.assertEqual([p['product_id'] for p in response['data']['items']], [product_id])
        self.assertEqual(self.request(f'/api/merchant/products/{product_id}', {'stock_quantity': 0, 'status': 'inactive'}, uid=1, method='PUT')[0], 200)
        self.assertEqual(self.request('/api/merchant/products/1', {'product_name': 'intrusion'}, uid=1, method='PUT')[0], 403)
        self.assertEqual(self.request('/api/products/1', {'product_name': 'intrusion'}, uid=1, method='PUT')[0], 403)
        self.assertEqual(self.request('/api/products/1', uid=1, method='DELETE')[0], 403)
        self.assertEqual(self.request('/api/merchant/products', payload, uid=4)[0], 403)
        self.assertEqual(self.request('/api/merchant/products/1', {'product_name': 'intrusion'}, uid=5, method='PUT')[0], 403)
        self.assertEqual(self.request('/api/merchant/products/1', {'stock_quantity': 8}, uid=2, method='PUT')[0], 200)
        with SessionLocal() as db:
            self.assertEqual(db.get(Product, 1).stock_quantity, 8)
            self.assertEqual(db.get(Product, 1).product_name, 'Product')

    def test_management_validation_shipping_and_audit_export(self):
        self.assertEqual(self.request('/api/admin/products/1', {'stock_quantity': -1}, uid=3, method='PUT')[0], 400)
        self.assertEqual(self.request('/api/admin/users/3', {'role': 'normal'}, uid=3, method='PATCH')[0], 400)
        self.assertEqual(self.request('/api/admin/orders/1/ship', {'tracking_number': 'TRACK123'}, uid=3)[0], 200)
        self.assertEqual(self.request('/api/admin/orders/1/ship', {'tracking_number': 'TRACK123'}, uid=3)[0], 409)
        response = self.client.get('/api/audit/export', HTTP_AUTHORIZATION='Bearer ' + self.token(4))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('secret', response.content.decode())
        with SessionLocal() as db:
            self.assertEqual(db.get(Order, 1).order_status, OrderStatus.SHIPPED)
            self.assertTrue(db.query(AuditEvent).filter_by(action='audit.export', user_id=4).first())

    def test_public_certificate_file_is_not_authentication(self):
        self.assertEqual(self.request('/api/auth/cert/file-login', {'username': 'user3', 'certificate_pem': 'public'})[0], 403)

    def test_orders_are_scoped_to_the_owner(self):
        own = self.client.get('/api/orders/1', HTTP_AUTHORIZATION='Bearer ' + self.token(1))
        self.assertEqual(own.status_code, 200)
        other = self.client.get('/api/orders/1', HTTP_AUTHORIZATION='Bearer ' + self.token(2))
        self.assertEqual(other.status_code, 403)

    def test_demo_sms_code_cannot_reset_privileged_password(self):
        status, _ = self.request('/api/users/reset-password', {'phone': '13800000003', 'code': '123456', 'new_password': 'ChangedPass123!'})
        self.assertEqual(status, 400)
        status, response = self.request('/api/auth/login', {'username': 'user3', 'password': 'TestPass123!'})
        self.assertEqual(status, 200)
        self.assertTrue(response['data']['mfa_required'])

    def test_auditor_mfa_failure_limit_persists_across_requests(self):
        _, response = self.request('/api/auth/login', {'username': 'user4', 'password': 'TestPass123!'})
        data = response['data']
        self.assertTrue(data['mfa_required'])
        for _ in range(5):
            self.assertEqual(self.request('/api/auth/mfa/verify', {'challenge': data['challenge'], 'code': 'invalid'})[0], 400)
        self.assertEqual(self.request('/api/auth/mfa/verify', {'challenge': data['challenge'], 'code': totp(data['secret'], int(time.time()) // 30)})[0], 429)
        self.assertEqual(self.request('/api/auth/login', {'username': 'user4', 'password': 'TestPass123!'})[0], 403)

    def test_spoofed_mtls_headers_are_rejected(self):
        path = '/api/auth/cert/mtls-login'
        response = self.client.post(path, json.dumps({'username': 'user3'}), content_type='application/json',
                                    HTTP_X_SSL_CLIENT_VERIFY='SUCCESS', HTTP_X_SSL_CLIENT_S_DN='CN=user3', HTTP_X_SSL_CLIENT_CERT='fake')
        self.assertEqual(response.status_code, 403)



    def test_rebind_requires_old_factor_and_revokes_old_session(self):
        with SessionLocal.begin() as db:
            state = state_for(db, 3)
            state.enabled = True
            state.secret = cipher().encrypt(b'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ').decode()
            state.recovery_hashes = json.dumps([digest('old-recovery')])
        old_token = self.token(3)
        status, response = self.request('/api/auth/mfa/rebind', {'code': 'old-recovery'}, token=old_token)
        self.assertEqual(status, 200, response)
        pending = response['data']
        self.assertEqual(self.client.get('/api/admin/users', HTTP_AUTHORIZATION='Bearer ' + old_token).status_code, 401)
        status, response = self.request('/api/auth/mfa/verify', {'challenge': pending['challenge'], 'code': totp(pending['secret'], int(time.time()) // 30)})
        self.assertEqual(status, 200, response)
        self.assertEqual(len(response['data']['recovery_codes']), 8)

    def test_logout_invalidates_token_without_redis(self):
        token = self.token(1)
        self.assertEqual(self.request('/api/auth/logout', {}, token=token)[0], 200)
        self.assertEqual(self.client.get('/api/users/profile', HTTP_AUTHORIZATION='Bearer ' + token).status_code, 401)


if __name__ == '__main__':
    unittest.main()
