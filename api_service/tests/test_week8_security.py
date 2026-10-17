"""Focused regression for week 8 changes; no real users or databases."""
import unittest
from django.test import RequestFactory, override_settings
from api_service.tests import test_course_security as course


class Week8SecurityTests(unittest.TestCase):
    setUp = course.CourseSecurityTests.setUp
    token = course.CourseSecurityTests.token
    request = course.CourseSecurityTests.request

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
