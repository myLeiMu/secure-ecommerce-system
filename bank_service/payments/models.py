from decimal import Decimal

from django.db import models
from django.utils import timezone


class BankAccount(models.Model):
    bank_account_id = models.BigAutoField(primary_key=True)
    account_number = models.CharField(max_length=32, unique=True)
    owner_name = models.CharField(max_length=80)
    pay_password = models.CharField(max_length=128)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bank_accounts"
        indexes = [
            models.Index(fields=["account_number"], name="ix_bank_accounts_number"),
            models.Index(fields=["is_active"], name="ix_bank_accounts_active"),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(balance__gte=0), name="check_bank_balance_positive"),
        ]

    def __str__(self):
        return f"{self.owner_name} ({self.account_number})"


class PaymentTransaction(models.Model):
    STATUS_PENDING = "pending"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_REFUNDED = "refunded"

    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
        (STATUS_REFUNDED, "Refunded"),
    )

    bank_transaction_id = models.BigAutoField(primary_key=True)
    transaction_id = models.CharField(max_length=100, unique=True)
    order_no = models.CharField(max_length=64, db_index=True)
    merchant_id = models.CharField(max_length=64, db_index=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    account_number = models.CharField(max_length=32, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    message = models.CharField(max_length=255, blank=True)
    request_payload = models.JSONField(default=dict)
    result_payload = models.JSONField(default=dict)
    encrypted_result = models.TextField(blank=True)
    return_url = models.URLField(blank=True)
    callback_url = models.URLField(blank=True)
    callback_status = models.CharField(max_length=20, blank=True)
    callback_response = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    paid_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bank_payment_transactions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["transaction_id"], name="ix_bank_txn_id"),
            models.Index(fields=["status"], name="ix_bank_txn_status"),
            models.Index(fields=["created_at"], name="ix_bank_txn_created_at"),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gte=0), name="check_bank_payment_amount_positive"),
        ]

    def __str__(self):
        return f"{self.transaction_id} {self.order_no} {self.status}"
