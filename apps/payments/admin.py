from django.contrib import admin

from .models import Payment, PlatformSettings


@admin.register(PlatformSettings)
class PlatformSettingsAdmin(admin.ModelAdmin):
    list_display = ("commission_percent", "updated_at")

    def has_add_permission(self, request):
        return not PlatformSettings.objects.exists()


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("order", "amount", "currency", "method", "status", "commission_percent", "commission_amount", "driver_amount", "created_at")
    list_filter = ("status", "method", "currency", "created_at")
    search_fields = ("order__id", "provider", "provider_reference", "order__client__username")
    readonly_fields = ("commission_percent", "commission_amount", "driver_amount", "created_at", "confirmed_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
