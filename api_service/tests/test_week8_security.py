"""Focused regression for week 8 changes; no real users or databases."""
import unittest
import os
from unittest.mock import patch
from sqlalchemy import text
from cryptography.fernet import InvalidToken
from django.test import RequestFactory, override_settings
from api_service.tests import test_course_security as course


class Week8SecurityTests(unittest.TestCase):
    setUp = course.CourseSecurityTests.setUp
    token = course.CourseSecurityTests.token
    request = course.CourseSecurityTests.request

    def test_bank_card_is_encrypted_in_database_and_tampering_fails(self):
        from src.Data_base.encrypted_fields import decrypt_card, encrypt_card
        card = '6222000000001234'
        with course.SessionLocal.begin() as db:
            db.get(course.User, 1).bank_card_number = card
        with course.engine.connect() as connection:
            stored = connection.execute(text('SELECT bank_card_number FROM users WHERE user_id=1')).scalar_one()
        self.assertTrue(stored.startswith('enc:v1:'))
        self.assertNotIn(card, stored)
        self.assertEqual(decrypt_card(stored), card)
        with course.SessionLocal() as db:
            self.assertEqual(db.get(course.User, 1).bank_card_number, card)
        with self.assertRaises(InvalidToken):
            decrypt_card(stored[:-4] + 'AAAA')
        with patch.dict(os.environ, {'BANK_CARD_ENCRYPTION_KEY': ''}):
            with self.assertRaises(RuntimeError):
                encrypt_card(card)
        with self.assertRaises(ValueError):
            decrypt_card(card)

    def test_untrusted_forwarded_host_is_ignored(self):
        request = RequestFactory().get('/api/products', HTTP_HOST='localhost',
                                       HTTP_X_FORWARDED_HOST='attacker.invalid')
        self.assertEqual(request.get_host(), 'localhost')

    def test_missing_payment_key_fails_closed(self):
        with override_settings(ECOMMERCE_MERCHANT_PRIVATE_KEY=''):
            for path in ('/api/orders/1/pay', '/api/pay/sync-result', '/api/pay/callback'):
                status, _ = self.request(path, {}, uid=1)
                self.assertEqual(status, 503, path)

    def test_cross_origin_response_does_not_grant_attacker_read_access(self):
        response = self.client.get('/api/users/profile',
                                   HTTP_AUTHORIZATION='Bearer ' + self.token(1),
                                   HTTP_ORIGIN='https://attacker.invalid')
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.headers.get('Access-Control-Allow-Origin'), 'https://attacker.invalid')
        self.assertNotEqual(response.headers.get('Access-Control-Allow-Origin'), '*')

    def test_admin_email_data_requires_administrator(self):
        self.assertEqual(self.client.get('/api/admin/users').status_code, 401)
        for uid in (1, 2, 4):
            response = self.client.get('/api/admin/users', HTTP_AUTHORIZATION='Bearer ' + self.token(uid))
            self.assertEqual(response.status_code, 403)
            self.assertNotIn(b'u1@example.com', response.content)
        response = self.client.get('/api/admin/users', HTTP_AUTHORIZATION='Bearer ' + self.token(3))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'u1@example.com', response.content)

    @override_settings(SECURE_SSL_REDIRECT=True, MTLS_PROXY_SECRET='test-gateway-secret')
    def test_http_and_spoofed_tls_headers_cannot_reach_login(self):
        for headers in ({}, {'HTTP_X_FORWARDED_PROTO': 'https'},
                        {'HTTP_X_FORWARDED_PROTO': 'https', 'HTTP_X_MTLS_PROXY_SECRET': 'wrong'}):
            response = self.client.post('/api/auth/login', {}, content_type='application/json', **headers)
            self.assertEqual(response.status_code, 426)
        response = self.client.get('/api/products', HTTP_HOST='localhost',
                                   HTTP_X_FORWARDED_HOST='attacker.invalid')
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.headers['Location'], 'https://localhost:8443/api/products')
        response = self.client.post('/api/auth/login', {'username': 'user1', 'password': 'TestPass123!'},
                                    content_type='application/json', HTTP_X_FORWARDED_PROTO='https',
                                    HTTP_X_MTLS_PROXY_SECRET='test-gateway-secret')
        self.assertEqual(response.status_code, 200)
        self.assertIn('max-age=86400', response.headers['Strict-Transport-Security'])

    def test_same_origin_proxy_needs_no_cors_allowlist(self):
        for origin in ('http://localhost:3000', 'https://localhost:3000', 'https://attacker.invalid'):
            response = self.client.get('/api/users/profile', HTTP_ORIGIN=origin,
                                       HTTP_AUTHORIZATION='Bearer ' + self.token(1))
            self.assertNotIn('Access-Control-Allow-Origin', response.headers)
            self.assertNotIn('Access-Control-Allow-Credentials', response.headers)
