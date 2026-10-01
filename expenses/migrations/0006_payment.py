from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from decimal import Decimal

class Migration(migrations.Migration):
    dependencies = [
        ("expenses", "0005_subscription_active"),
    ]

    operations = [
        migrations.CreateModel(
            name="Payment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order_id", models.CharField(max_length=80, unique=True)),
                ("payment_id", models.CharField(blank=True, max_length=80)),
                ("signature", models.CharField(blank=True, max_length=255)),
                ("amount", models.DecimalField(decimal_places=2, default=Decimal("99.00"), max_digits=10)),
                ("status", models.CharField(choices=[("created", "Created"), ("paid", "Paid"), ("failed", "Failed")], default="created", max_length=20)),
                ("purpose", models.CharField(default="access", max_length=50)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="payments", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
