from django.contrib.gis.admin import GISModelAdmin
from django.contrib import admin
from .models import ServiceZone


@admin.register(ServiceZone)
class ServiceZoneAdmin(GISModelAdmin):
    list_display = ("name", "code", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")
