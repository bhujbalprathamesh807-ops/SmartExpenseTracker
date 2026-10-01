from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("expenses", "0002_contactmessage"),
    ]

    operations = [
        migrations.CreateModel(
            name="EMI",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("lender", models.CharField(max_length=120)),
                ("loan_name", models.CharField(max_length=150)),
                ("principal", models.DecimalField(decimal_places=2, max_digits=12)),
                ("annual_interest_rate", models.DecimalField(decimal_places=2, default=0, max_digits=6)),
                ("tenure_months", models.PositiveIntegerField()),
                ("start_date", models.DateField(default=django.utils.timezone.localdate)),
                ("monthly_emi", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("total_interest", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("total_payable", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("paid_installments", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="emis", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
