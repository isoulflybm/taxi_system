from django.contrib.gis.db import models
from django.utils import timezone

from apps.accounts.models import UserProfile


class DriverLocation(models.Model):
    driver = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="location_updates", limit_choices_to={"role": UserProfile.Role.DRIVER})
    location = models.PointField(srid=4326)
    heading = models.PositiveSmallIntegerField(null=True, blank=True)
    speed_mps = models.FloatField(null=True, blank=True)
    accuracy_m = models.FloatField(null=True, blank=True)
    recorded_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ("-recorded_at",)
        indexes = [
            models.Index(fields=("driver", "recorded_at"), name="driver_recorded_at_idx"),
        ]

    def __str__(self):
        return f"{self.driver} @ {self.recorded_at}"
