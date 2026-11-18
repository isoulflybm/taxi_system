import decimal

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [("orders", "0002_route_assignment_snapshots")]

    operations = [
        migrations.CreateModel(
            name="PlatformSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("commission_percent", models.DecimalField(decimal_places=2, default=decimal.Decimal("0.00"), max_digits=5, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)], verbose_name="Комиссия сервиса, %")),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "Настройки комиссии", "verbose_name_plural": "Настройки комиссии"},
        ),
        migrations.CreateModel(
            name="Payment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("method", models.CharField(choices=[("cash", "Наличные"), ("card", "Карта"), ("wallet", "Электронный кошелёк"), ("manual", "Внесён вручную")], default="cash", max_length=16)),
                ("status", models.CharField(choices=[("pending", "Ожидает подтверждения"), ("succeeded", "Успешно оплачен"), ("failed", "Ошибка оплаты"), ("refunded", "Возврат")], db_index=True, default="pending", max_length=16)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0.01"))])),
                ("currency", models.CharField(default="KGS", max_length=3)),
                ("commission_percent", models.DecimalField(decimal_places=2, default=decimal.Decimal("0.00"), max_digits=5)),
                ("commission_amount", models.DecimalField(decimal_places=2, default=decimal.Decimal("0.00"), max_digits=10)),
                ("driver_amount", models.DecimalField(decimal_places=2, default=decimal.Decimal("0.00"), max_digits=10)),
                ("provider", models.CharField(blank=True, max_length=64)),
                ("provider_reference", models.CharField(blank=True, max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("confirmed_at", models.DateTimeField(blank=True, null=True)),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payments", to="orders.order")),
            ],
            options={"ordering": ("-created_at",)},
        ),
    ]
