from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0004_refunded_status"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="bankaccount",
            name="sm2_private_key",
        ),
        migrations.RemoveField(
            model_name="bankaccount",
            name="sm2_public_key",
        ),
    ]
