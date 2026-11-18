from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import UserProfile
from apps.orders.models import Order
from apps.tracking.models import DriverLocation
from .permissions import can_dispatch


@login_required
def map_dashboard(request):
    if not can_dispatch(request.user):
        return HttpResponseForbidden("Доступ только для диспетчера.")
    return render(request, "dispatch/map.html", {
        "map_style_url": settings.MAP_STYLE_URL,
        "geocoding_enabled": bool(settings.NOMINATIM_BASE_URL),
    })


class MapSnapshotAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        if not can_dispatch(request.user):
            raise PermissionDenied("Доступ только для диспетчера.")

        active_orders = Order.objects.exclude(
            status__in=(Order.Status.COMPLETED, Order.Status.CANCELLED)
        ).select_related("client", "assigned_driver").order_by("-created_at")[:500]
        orders = [{
            "id": str(order.id),
            "status": order.status,
            "status_label": order.get_status_display(),
            "pickup": {"latitude": order.pickup.y, "longitude": order.pickup.x},
            "dropoff": {"latitude": order.dropoff.y, "longitude": order.dropoff.x},
            "pickup_address": order.pickup_address,
            "dropoff_address": order.dropoff_address,
            "route_geojson": order.route_geojson,
            "client": order.client.get_username(),
            "driver": order.assigned_driver.user.get_username() if order.assigned_driver else None,
            "price": str(order.estimated_price) if order.estimated_price is not None else None,
            "currency": order.currency,
            "created_at": order.created_at.isoformat(),
        } for order in active_orders]

        latest_locations = DriverLocation.objects.filter(
            driver__role=UserProfile.Role.DRIVER,
            recorded_at__gte=timezone.now() - timedelta(minutes=2),
        ).select_related("driver__user").order_by("driver_id", "-recorded_at").distinct("driver_id")
        drivers = [{
            "driver_id": location.driver_id,
            "username": location.driver.user.get_username(),
            "latitude": location.location.y,
            "longitude": location.location.x,
            "heading": location.heading,
            "speed_mps": location.speed_mps,
            "accuracy_m": location.accuracy_m,
            "recorded_at": location.recorded_at.isoformat(),
        } for location in latest_locations]
        return Response({"orders": orders, "drivers": drivers})
