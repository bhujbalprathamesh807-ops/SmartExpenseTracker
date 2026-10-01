from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("expenses", "0006_payment"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="trial_started_at",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
