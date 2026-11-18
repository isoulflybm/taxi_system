from django.contrib import admin
from .models import Tariff


@admin.register(Tariff)
class TariffAdmin(admin.ModelAdmin):
    list_display = ("name", "zone", "base_fare", "per_km", "per_minute", "minimum_fare", "currency", "is_active")
    list_filter = ("is_active", "currency", "zone")
    search_fields = ("name",)
