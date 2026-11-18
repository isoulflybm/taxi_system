from django.contrib import admin
from .models import Vehicle


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("plate_number", "make", "model", "driver", "state", "seats")
    list_filter = ("state", "make")
    search_fields = ("plate_number", "make", "model", "driver__user__username")
