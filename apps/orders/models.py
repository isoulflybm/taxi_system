import uuid

from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models

from apps.accounts.models import UserProfile
from apps.geo.models import ServiceZone
from apps.tariffs.models import Tariff


class Order(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Новый"
        ASSIGNED = "assigned", "Назначен водитель"
        DRIVER_ARRIVING = "driver_arriving", "Водитель едет к клиенту"
        IN_PROGRESS = "in_progress", "Поездка началась"
        COMPLETED = "completed", "Завершён"
        CANCELLED = "cancelled", "Отменён"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="taxi_orders")
    assigned_driver = models.ForeignKey(UserProfile, on_delete=models.PROTECT, null=True, blank=True, related_name="assigned_orders", limit_choices_to={"role": UserProfile.Role.DRIVER})
    tariff = models.ForeignKey(Tariff, on_delete=models.PROTECT, null=True, blank=True, related_name="orders")
    service_zone = models.ForeignKey(ServiceZone, on_delete=models.PROTECT, null=True, blank=True, related_name="orders")
    pickup = gis_models.PointField(srid=4326)
    dropoff = gis_models.PointField(srid=4326)
    pickup_address = models.CharField(max_length=255, blank=True)
    dropoff_address = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.NEW, db_index=True)
    estimated_distance_m = models.PositiveIntegerField(null=True, blank=True)
    estimated_duration_s = models.PositiveIntegerField(null=True, blank=True)
    estimated_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    final_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    route_geojson = models.JSONField(null=True, blank=True)
    tariff_snapshot = models.JSONField(default=dict, blank=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    currency = models.CharField(max_length=3, default="KGS")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("status", "created_at"), name="order_status_created_idx")]

    def __str__(self):
        return f"{self.id} — {self.get_status_display()}"


class DriverDecline(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="driver_declines")
    driver = models.ForeignKey(UserProfile, on_delete=models.PROTECT, related_name="order_declines", limit_choices_to={"role": UserProfile.Role.DRIVER})
    declined_at = models.DateTimeField(auto_now_add=True)
    reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("-declined_at",)
        constraints = [models.UniqueConstraint(fields=("order", "driver"), name="unique_order_driver_decline")]
        indexes = [models.Index(fields=("order", "declined_at"), name="order_decline_time_idx")]

    def __str__(self):
        return f"{self.driver} отказался от {self.order_id}"
