from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0002_bankaccount_sm2_keys"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="paymenttransaction",
            name="result_signature",
        ),
        migrations.AddField(
            model_name="paymenttransaction",
            name="callback_url",
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name="paymenttransaction",
            name="callback_status",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name="paymenttransaction",
            name="callback_response",
            field=models.TextField(blank=True),
        ),
    ]
