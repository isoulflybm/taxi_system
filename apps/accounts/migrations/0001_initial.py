import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [migrations.CreateModel(
        name="UserProfile",
        fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("role", models.CharField(choices=[("customer", "Клиент"), ("driver", "Водитель"), ("dispatcher", "Диспетчер"), ("admin", "Администратор")], db_index=True, default="customer", max_length=20)),
            ("phone", models.CharField(blank=True, max_length=32, null=True, unique=True)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="taxi_profile", to=settings.AUTH_USER_MODEL)),
        ],
    )]
