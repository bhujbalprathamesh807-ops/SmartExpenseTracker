from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("expenses", "0003_emi"),
    ]

    operations = [
        migrations.AddField(
            model_name="transaction",
            name="receipt_image",
            field=models.ImageField(blank=True, null=True, upload_to="receipts/"),
        ),
        migrations.AddField(
            model_name="transaction",
            name="receipt_items",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="transaction",
            name="receipt_number",
            field=models.CharField(blank=True, max_length=120),
        ),
    ]
