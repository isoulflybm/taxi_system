from django.contrib.gis.db import models as gis_models
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [migrations.CreateModel(
        name="ServiceZone",
        fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("name", models.CharField(max_length=120)),
            ("code", models.SlugField(max_length=80, unique=True)),
            ("boundary", gis_models.MultiPolygonField(srid=4326)),
            ("is_active", models.BooleanField(db_index=True, default=True)),
        ],
        options={"ordering": ("name",)},
    )]
