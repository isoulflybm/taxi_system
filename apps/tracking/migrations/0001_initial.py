import django.contrib.gis.db.models.fields
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [("accounts", "0001_initial")]
    operations = [migrations.CreateModel(
        name="DriverLocation",
        fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("location", django.contrib.gis.db.models.fields.PointField(srid=4326)),
            ("heading", models.PositiveSmallIntegerField(blank=True, null=True)),
            ("speed_mps", models.FloatField(blank=True, null=True)),
            ("recorded_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ("driver", models.ForeignKey(limit_choices_to={"role": "driver"}, on_delete=django.db.models.deletion.CASCADE, related_name="location_updates", to="accounts.userprofile")),
        ],
        options={
            "ordering": ("-recorded_at",),
            "indexes": [
                models.Index(fields=["driver", "recorded_at"], name="driver_recorded_at_idx"),
            ],
        },
    )]
