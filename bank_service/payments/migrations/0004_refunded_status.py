from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0003_callback_fields_remove_result_signature"),
    ]

    operations = [
        migrations.AlterField(
            model_name="paymenttransaction",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("success", "Success"),
                    ("failed", "Failed"),
                    ("refunded", "Refunded"),
                ],
                default="pending",
                max_length=16,
            ),
        ),
    ]
