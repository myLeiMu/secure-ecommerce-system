import time
from decimal import Decimal
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.conf import settings
from django.test import Client, TestCase
from django.urls import reverse

from .models import BankAccount, PaymentTransaction
from .security import get_merchant_private_key, open_result_envelope, sign_params


class PaymentFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.account = BankAccount.objects.create(
            account_number="6222000000000001",
            owner_name="Test Buyer",
            pay_password="123456",
            balance=Decimal("100.00"),
        )

    def signed_params(self, **overrides):
        merchant_id = overrides.pop("merchant_id", "ECOMMERCE_DEMO")
        params = {
            "order_no": "ORD10001",
            "amount": "25.50",
            "merchant_id": merchant_id,
            "timestamp": str(int(time.time())),
            "return_url": "http://127.0.0.1:8000/pay/result",
            "callback_url": "http://127.0.0.1:8080/api/pay/callback",
        }
        params.update(overrides)
        params["signature"] = sign_params(params, get_merchant_private_key(merchant_id))
        return params

    def test_pay_page_accepts_valid_signed_request(self):
        response = self.client.get(reverse("pay-page"), self.signed_params())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "模拟银行支付")
        self.assertContains(response, "ORD10001")

    def test_pay_page_rejects_bad_signature(self):
        params = self.signed_params()
        params["signature"] = "bad"

        response = self.client.get(reverse("pay-page"), params)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "支付请求 SM2 签名校验失败")

    def test_pay_page_rejects_expired_timestamp(self):
        expired_timestamp = str(int(time.time()) - settings.BANK_PAYMENT_TIMESTAMP_VALID_SECONDS - 1)
        params = self.signed_params(timestamp=expired_timestamp)

        response = self.client.get(reverse("pay-page"), params)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "支付请求已过期")

    @patch("payments.views.requests.post")
    def test_process_payment_redirects_and_posts_same_digital_envelope(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = "ok"
        params = self.signed_params()

        response = self.client.post(
            reverse("pay-process"),
            {
                **params,
                "account_number": self.account.account_number,
                "pay_password": "123456",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal("74.50"))

        payment = PaymentTransaction.objects.get(order_no="ORD10001")
        self.assertEqual(payment.status, PaymentTransaction.STATUS_SUCCESS)
        self.assertEqual(payment.callback_status, "success")

        location_params = parse_qs(urlparse(response["Location"]).query)
        self.assertIn("encrypted_key", location_params)
        self.assertIn("iv", location_params)
        self.assertIn("data", location_params)
        self.assertNotIn("result_signature", location_params)

        callback_payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(callback_payload["encrypted_key"], location_params["encrypted_key"][0])
        self.assertEqual(callback_payload["iv"], location_params["iv"][0])
        self.assertEqual(callback_payload["data"], location_params["data"][0])

        decrypted = open_result_envelope(callback_payload, get_merchant_private_key("ECOMMERCE_DEMO"))
        self.assertEqual(decrypted["order_no"], "ORD10001")
        self.assertEqual(decrypted["status"], PaymentTransaction.STATUS_SUCCESS)
        self.assertEqual(decrypted["bank_transaction_id"], payment.transaction_id)
        self.assertIn("timestamp", decrypted)

    @patch("payments.views.requests.post")
    def test_process_payment_fails_on_low_balance(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = "ok"
        params = self.signed_params(amount="1000.00")
        response = self.client.post(
            reverse("pay-process"),
            {
                **params,
                "account_number": self.account.account_number,
                "pay_password": "123456",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal("100.00"))
        payment = PaymentTransaction.objects.get(order_no="ORD10001")
        self.assertEqual(payment.status, PaymentTransaction.STATUS_FAILED)
        self.assertEqual(payment.message, "账户余额不足")
