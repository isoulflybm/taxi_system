import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [("accounts", "0001_initial")]
    operations = [migrations.CreateModel(
        name="Vehicle",
        fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("plate_number", models.CharField(max_length=24, unique=True)),
            ("make", models.CharField(max_length=60)),
            ("model", models.CharField(max_length=60)),
            ("color", models.CharField(blank=True, max_length=32)),
            ("seats", models.PositiveSmallIntegerField(default=4)),
            ("state", models.CharField(choices=[("active", "Активен"), ("maintenance", "На обслуживании"), ("inactive", "Не используется")], db_index=True, default="active", max_length=20)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("driver", models.ForeignKey(blank=True, limit_choices_to={"role": "driver"}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="vehicles", to="accounts.userprofile")),
        ],
    )]
