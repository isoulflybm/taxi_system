from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from .models import DriverLocation


@admin.register(DriverLocation)
class DriverLocationAdmin(GISModelAdmin):
    list_display = ("driver", "recorded_at", "heading", "speed_mps")
    list_filter = ("recorded_at",)
    search_fields = ("driver__user__username",)
    readonly_fields = ("recorded_at",)
