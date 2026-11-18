import uuid
import django.contrib.gis.db.models.fields
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0001_initial"),
        ("geo", "0001_initial"),
        ("tariffs", "0001_initial"),
    ]
    operations = [migrations.CreateModel(
        name="Order",
        fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ("pickup", django.contrib.gis.db.models.fields.PointField(srid=4326)),
            ("dropoff", django.contrib.gis.db.models.fields.PointField(srid=4326)),
            ("pickup_address", models.CharField(blank=True, max_length=255)),
            ("dropoff_address", models.CharField(blank=True, max_length=255)),
            ("status", models.CharField(choices=[("new", "Новый"), ("assigned", "Назначен водитель"), ("driver_arriving", "Водитель едет к клиенту"), ("in_progress", "Поездка началась"), ("completed", "Завершён"), ("cancelled", "Отменён")], db_index=True, default="new", max_length=24)),
            ("estimated_distance_m", models.PositiveIntegerField(blank=True, null=True)),
            ("estimated_duration_s", models.PositiveIntegerField(blank=True, null=True)),
            ("estimated_price", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
            ("final_price", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
            ("currency", models.CharField(default="KGS", max_length=3)),
            ("notes", models.TextField(blank=True)),
            ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ("updated_at", models.DateTimeField(auto_now=True)),
            ("assigned_driver", models.ForeignKey(blank=True, limit_choices_to={"role": "driver"}, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="assigned_orders", to="accounts.userprofile")),
            ("client", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="taxi_orders", to=settings.AUTH_USER_MODEL)),
            ("service_zone", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="orders", to="geo.servicezone")),
            ("tariff", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="orders", to="tariffs.tariff")),
        ],
        options={"ordering": ("-created_at",), "indexes": [models.Index(fields=["status", "created_at"], name="order_status_created_idx")]},
    )]
