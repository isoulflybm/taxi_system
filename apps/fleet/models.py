from django.db import models

from apps.accounts.models import UserProfile


class Vehicle(models.Model):
    class State(models.TextChoices):
        ACTIVE = "active", "Активен"
        MAINTENANCE = "maintenance", "На обслуживании"
        INACTIVE = "inactive", "Не используется"

    driver = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="vehicles", limit_choices_to={"role": UserProfile.Role.DRIVER})
    plate_number = models.CharField(max_length=24, unique=True)
    make = models.CharField(max_length=60)
    model = models.CharField(max_length=60)
    color = models.CharField(max_length=32, blank=True)
    seats = models.PositiveSmallIntegerField(default=4)
    state = models.CharField(max_length=20, choices=State.choices, default=State.ACTIVE, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.plate_number} — {self.make} {self.model}"
