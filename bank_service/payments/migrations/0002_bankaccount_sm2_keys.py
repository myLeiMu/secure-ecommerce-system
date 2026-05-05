from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="bankaccount",
            name="sm2_private_key",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="bankaccount",
            name="sm2_public_key",
            field=models.CharField(blank=True, max_length=128),
        ),
    ]
