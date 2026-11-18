from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("orders", "0001_initial")]

    operations = [
        migrations.AddField(model_name="order", name="route_geojson", field=models.JSONField(blank=True, null=True)),
        migrations.AddField(model_name="order", name="tariff_snapshot", field=models.JSONField(blank=True, default=dict)),
        migrations.AddField(model_name="order", name="assigned_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="order", name="cancelled_at", field=models.DateTimeField(blank=True, null=True)),
    ]
