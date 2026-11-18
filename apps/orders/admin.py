from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from .models import DriverDecline, Order


@admin.register(Order)
class OrderAdmin(GISModelAdmin):
    list_display = ("id", "client", "status", "assigned_driver", "estimated_price", "currency", "created_at")
    list_filter = ("status", "currency", "created_at")
    search_fields = ("id", "client__username", "pickup_address", "dropoff_address", "assigned_driver__user__username")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(DriverDecline)
class DriverDeclineAdmin(admin.ModelAdmin):
    list_display = ("order", "driver", "declined_at", "reason")
    search_fields = ("order__id", "driver__user__username")
    readonly_fields = ("order", "driver", "declined_at", "reason")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
