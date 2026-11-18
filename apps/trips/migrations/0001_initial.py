import django.contrib.gis.db.models.fields
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [("accounts", "0001_initial"), ("fleet", "0001_initial"), ("orders", "0001_initial")]
    operations = [migrations.CreateModel(
        name="Trip",
        fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("status", models.CharField(choices=[("active", "Выполняется"), ("completed", "Завершена"), ("cancelled", "Отменена")], db_index=True, default="active", max_length=16)),
            ("started_at", models.DateTimeField(blank=True, null=True)),
            ("finished_at", models.DateTimeField(blank=True, null=True)),
            ("start_position", django.contrib.gis.db.models.fields.PointField(blank=True, null=True, srid=4326)),
            ("finish_position", django.contrib.gis.db.models.fields.PointField(blank=True, null=True, srid=4326)),
            ("actual_distance_m", models.PositiveIntegerField(blank=True, null=True)),
            ("final_price", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("driver", models.ForeignKey(limit_choices_to={"role": "driver"}, on_delete=django.db.models.deletion.PROTECT, related_name="trips", to="accounts.userprofile")),
            ("order", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="trip", to="orders.order")),
            ("vehicle", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="trips", to="fleet.vehicle")),
        ],
        options={"ordering": ("-created_at",)},
    )]
