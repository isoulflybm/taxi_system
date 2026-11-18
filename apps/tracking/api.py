from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.utils import timezone
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import UserProfile
from apps.orders.models import Order
from apps.orders.services import try_assign_nearest_driver
from .models import DriverLocation
from .serializers import DriverLocationInputSerializer


class DriverLocationAPIView(APIView):
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "driver_location"

    def post(self, request):
        profile = getattr(request.user, "taxi_profile", None)
        if not profile or profile.role != UserProfile.Role.DRIVER:
            raise PermissionDenied("Передавать координаты может только водитель.")

        serializer = DriverLocationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        point = Point(values["longitude"], values["latitude"], srid=4326)
        location = DriverLocation.objects.create(
            driver=profile,
            location=point,
            heading=values.get("heading"),
            speed_mps=values.get("speed_mps"),
            accuracy_m=values.get("accuracy_m"),
            recorded_at=values.get("recorded_at", timezone.now()),
        )
        driver_is_busy = Order.objects.filter(
            assigned_driver=profile,
            status__in=(Order.Status.ASSIGNED, Order.Status.DRIVER_ARRIVING, Order.Status.IN_PROGRESS),
        ).exists()
        if not driver_is_busy:
            # Retry a small oldest-first batch when an idle driver reports a fresh position.
            pending = Order.objects.filter(
                status=Order.Status.NEW,
                pickup__distance_lte=(location.location, D(m=settings.DRIVER_SEARCH_RADIUS_METERS)),
            ).order_by("created_at")[:10]
            for order in pending:
                assigned = try_assign_nearest_driver(order)
                if assigned.assigned_driver_id:
                    break
        payload = {
            "event": "driver_location",
            "driver_id": profile.pk,
            "username": request.user.get_username(),
            "latitude": location.location.y,
            "longitude": location.location.x,
            "heading": location.heading,
            "speed_mps": location.speed_mps,
            "accuracy_m": location.accuracy_m,
            "recorded_at": location.recorded_at.isoformat(),
        }
        async_to_sync(get_channel_layer().group_send)(
            "dispatch_map", {"type": "driver.location", "data": payload}
        )
        return Response({"status": "ok", "recorded_at": payload["recorded_at"]}, status=status.HTTP_201_CREATED)
