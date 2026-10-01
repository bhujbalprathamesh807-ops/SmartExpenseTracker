from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("expenses", "0004_transaction_receipt_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="subscription_active",
            field=models.BooleanField(default=False),
        ),
    ]
