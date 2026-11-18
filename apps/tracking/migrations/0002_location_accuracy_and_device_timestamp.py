import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("tracking", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="driverlocation",
            name="accuracy_m",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="driverlocation",
            name="recorded_at",
            field=models.DateTimeField(db_index=True, default=django.utils.timezone.now),
        ),
    ]
