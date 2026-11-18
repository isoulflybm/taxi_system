from django.core.validators import MinValueValidator
from django.db import models

from apps.geo.models import ServiceZone


class Tariff(models.Model):
    name = models.CharField(max_length=100)
    zone = models.ForeignKey(ServiceZone, on_delete=models.PROTECT, null=True, blank=True, related_name="tariffs")
    base_fare = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    per_km = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    per_minute = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    minimum_fare = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=3, default="KGS")
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return f"{self.name} ({self.currency})"
