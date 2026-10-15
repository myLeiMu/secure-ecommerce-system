from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0005_remove_bankaccount_sm2_keys"),
    ]

    operations = [
        migrations.AddField(
            model_name="paymenttransaction",
            name="successful_order_key",
            field=models.CharField(blank=True, max_length=140, null=True, unique=True),
        ),
        migrations.AddIndex(
            model_name="paymenttransaction",
            index=models.Index(fields=["merchant_id", "order_no"], name="ix_bank_txn_order"),
        ),
    ]
