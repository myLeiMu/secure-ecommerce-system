from decimal import Decimal

from django.core.management.base import BaseCommand

from payments.models import BankAccount


class Command(BaseCommand):
    help = "Create demo bank accounts for local payment testing."

    def handle(self, *args, **options):
        accounts = [
            {
                "account_number": "6222000000000001",
                "owner_name": "Test Buyer",
                "pay_password": "123456",
                "balance": Decimal("10000.00"),
            },
            {
                "account_number": "6222000000000002",
                "owner_name": "Low Balance Buyer",
                "pay_password": "123456",
                "balance": Decimal("10.00"),
            },
            {
                "account_number": "6222000000000003",
                "owner_name": "testuser",
                "pay_password": "123456",
                "balance": Decimal("500000.00"),
                "is_active": True,
            },
        ]
        for data in accounts:
            account, created = BankAccount.objects.update_or_create(
                account_number=data["account_number"],
                defaults=data,
            )
            action = "created" if created else "updated"
            self.stdout.write(
                self.style.SUCCESS(
                    f"{action}: {account.account_number} balance={account.balance} password={account.pay_password}"
                )
            )
