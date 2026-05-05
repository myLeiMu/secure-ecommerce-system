from decimal import Decimal

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="BankAccount",
            fields=[
                ("bank_account_id", models.BigAutoField(primary_key=True, serialize=False)),
                ("account_number", models.CharField(max_length=32, unique=True)),
                ("owner_name", models.CharField(max_length=80)),
                ("pay_password", models.CharField(max_length=128)),
                ("balance", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "bank_accounts",
            },
        ),
        migrations.CreateModel(
            name="PaymentTransaction",
            fields=[
                ("bank_transaction_id", models.BigAutoField(primary_key=True, serialize=False)),
                ("transaction_id", models.CharField(max_length=100, unique=True)),
                ("order_no", models.CharField(db_index=True, max_length=64)),
                ("merchant_id", models.CharField(db_index=True, max_length=64)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("account_number", models.CharField(blank=True, max_length=32)),
                (
                    "status",
                    models.CharField(
                        choices=[("pending", "Pending"), ("success", "Success"), ("failed", "Failed")],
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("message", models.CharField(blank=True, max_length=255)),
                ("request_payload", models.JSONField(default=dict)),
                ("result_payload", models.JSONField(default=dict)),
                ("encrypted_result", models.TextField(blank=True)),
                ("result_signature", models.CharField(blank=True, max_length=128)),
                ("return_url", models.URLField(blank=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "bank_payment_transactions",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="bankaccount",
            index=models.Index(fields=["account_number"], name="ix_bank_accounts_number"),
        ),
        migrations.AddIndex(
            model_name="bankaccount",
            index=models.Index(fields=["is_active"], name="ix_bank_accounts_active"),
        ),
        migrations.AddConstraint(
            model_name="bankaccount",
            constraint=models.CheckConstraint(condition=models.Q(("balance__gte", 0)), name="check_bank_balance_positive"),
        ),
        migrations.AddIndex(
            model_name="paymenttransaction",
            index=models.Index(fields=["transaction_id"], name="ix_bank_txn_id"),
        ),
        migrations.AddIndex(
            model_name="paymenttransaction",
            index=models.Index(fields=["status"], name="ix_bank_txn_status"),
        ),
        migrations.AddIndex(
            model_name="paymenttransaction",
            index=models.Index(fields=["created_at"], name="ix_bank_txn_created_at"),
        ),
        migrations.AddConstraint(
            model_name="paymenttransaction",
            constraint=models.CheckConstraint(condition=models.Q(("amount__gte", 0)), name="check_bank_payment_amount_positive"),
        ),
    ]
