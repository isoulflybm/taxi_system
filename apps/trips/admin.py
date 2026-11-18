from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from .models import Trip


@admin.register(Trip)
class TripAdmin(GISModelAdmin):
    list_display = ("order", "driver", "vehicle", "status", "started_at", "finished_at", "final_price")
    list_filter = ("status",)
    search_fields = ("order__id", "driver__user__username", "vehicle__plate_number")
