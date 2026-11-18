from django.contrib.gis.db import models as gis_models
from django.db import models

from apps.accounts.models import UserProfile
from apps.fleet.models import Vehicle
from apps.orders.models import Order


class Trip(models.Model):
    class Status(models.TextChoices):
        ASSIGNED = "assigned", "Назначена"
        ACTIVE = "active", "Выполняется"
        COMPLETED = "completed", "Завершена"
        CANCELLED = "cancelled", "Отменена"

    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name="trip")
    driver = models.ForeignKey(UserProfile, on_delete=models.PROTECT, related_name="trips", limit_choices_to={"role": UserProfile.Role.DRIVER})
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name="trips")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    passenger_picked_up_at = models.DateTimeField(null=True, blank=True)
    start_position = gis_models.PointField(srid=4326, null=True, blank=True)
    finish_position = gis_models.PointField(srid=4326, null=True, blank=True)
    actual_distance_m = models.PositiveIntegerField(null=True, blank=True)
    final_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Поездка по заказу {self.order_id}"
