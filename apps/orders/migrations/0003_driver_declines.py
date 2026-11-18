import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("orders", "0002_route_assignment_snapshots"),
    ]

    operations = [
        migrations.CreateModel(
            name="DriverDecline",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("declined_at", models.DateTimeField(auto_now_add=True)),
                ("reason", models.CharField(blank=True, max_length=255)),
                ("driver", models.ForeignKey(limit_choices_to={"role": "driver"}, on_delete=django.db.models.deletion.PROTECT, related_name="order_declines", to="accounts.userprofile")),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="driver_declines", to="orders.order")),
            ],
            options={"ordering": ("-declined_at",)},
        ),
        migrations.AddConstraint(
            model_name="driverdecline",
            constraint=models.UniqueConstraint(fields=("order", "driver"), name="unique_order_driver_decline"),
        ),
        migrations.AddIndex(
            model_name="driverdecline",
            index=models.Index(fields=["order", "declined_at"], name="order_decline_time_idx"),
        ),
    ]
