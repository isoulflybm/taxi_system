import hashlib
import json
from decimal import Decimal, InvalidOperation

from django.core.cache import cache
from rest_framework import serializers
from rest_framework.exceptions import Throttled
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from datetime import timedelta
from django.conf import settings
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.utils import timezone
from apps.accounts.models import UserProfile
from apps.fleet.models import Vehicle
from apps.orders.models import Order
from apps.tracking.models import DriverLocation

from apps.tariffs.models import Tariff
from apps.tariffs.services import calculate_fare, resolve_tariff
from .services import GeoServiceError, get_driving_route, search_addresses


def _coordinate(value, name, minimum, maximum):
    try:
        number = Decimal(value)
    except (InvalidOperation, TypeError):
        raise serializers.ValidationError({name: "Укажите корректное число."})
    if not number.is_finite() or not minimum <= number <= maximum:
        raise serializers.ValidationError({name: f"Значение должно быть от {minimum} до {maximum}."})
    return float(number)


class AddressSearchAPIView(APIView):
    permission_classes = (AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "geo_search"

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if not query or len(query) > 200:
            return Response({"detail": "Укажите адрес длиной от 1 до 200 символов."}, status=400)
        cache_key = "geo-search:" + hashlib.sha256(query.casefold().encode("utf-8")).hexdigest()
        cached = cache.get(cache_key)
        if cached is not None:
            return Response({"results": cached, "cached": True})
        # Nominatim-compatible backends should be self-hosted for production use.
        if not cache.add("nominatim-request-slot", "busy", timeout=1):
            raise Throttled(wait=1)
        try:
            results = search_addresses(query)
        except GeoServiceError as exc:
            return Response({"detail": str(exc)}, status=503)
        cache.set(cache_key, results, timeout=6 * 60 * 60)
        return Response({"results": results, "cached": False})


class RouteQuoteAPIView(APIView):
    permission_classes = (AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "public_route"

    def get(self, request):
        values = {
            "start_lon": _coordinate(request.query_params.get("start_lon"), "start_lon", -180, 180),
            "start_lat": _coordinate(request.query_params.get("start_lat"), "start_lat", -90, 90),
            "end_lon": _coordinate(request.query_params.get("end_lon"), "end_lon", -180, 180),
            "end_lat": _coordinate(request.query_params.get("end_lat"), "end_lat", -90, 90),
        }
        cache_key = "route:" + hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()
        route = cache.get(cache_key)
        if route is None:
            try:
                route = get_driving_route(**values)
            except GeoServiceError as exc:
                return Response({"detail": str(exc)}, status=503)
            cache.set(cache_key, route, timeout=15 * 60)
        tariff_id = request.query_params.get("tariff")
        requested_tariff = Tariff.objects.filter(pk=tariff_id, is_active=True).first() if tariff_id else None
        tariff = resolve_tariff(Point(values["start_lon"], values["start_lat"], srid=4326), requested_tariff)
        price = calculate_fare(tariff, route["distance_m"], route["duration_s"]) if tariff else None
        return Response({
            **route,
            "price": str(price) if price is not None else None,
            "currency": tariff.currency if tariff else "KGS",
            "tariff_id": tariff.pk if tariff else None,
            "tariff_name": tariff.name if tariff else None,
        })


class NearbyDriversAPIView(APIView):
    """Expose only an availability count; never publish precise driver positions to guests."""
    permission_classes = (AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "public_route"

    def get(self, request):
        lat = _coordinate(request.query_params.get("lat"), "lat", -90, 90)
        lon = _coordinate(request.query_params.get("lon"), "lon", -180, 180)
        point = Point(lon, lat, srid=4326)
        cutoff = timezone.now() - timedelta(seconds=settings.DRIVER_LOCATION_MAX_AGE_SECONDS)
        busy_ids = Order.objects.filter(
            status__in=(Order.Status.ASSIGNED, Order.Status.DRIVER_ARRIVING, Order.Status.IN_PROGRESS),
            assigned_driver__isnull=False,
        ).values_list("assigned_driver_id", flat=True)
        vehicle_driver_ids = Vehicle.objects.filter(state=Vehicle.State.ACTIVE, driver__isnull=False).values_list("driver_id", flat=True)
        online = DriverLocation.objects.filter(
            driver__role=UserProfile.Role.DRIVER,
            driver_id__in=vehicle_driver_ids,
            recorded_at__gte=cutoff,
            location__distance_lte=(point, D(m=settings.DRIVER_SEARCH_RADIUS_METERS)),
        ).exclude(driver_id__in=busy_ids).annotate(distance=Distance("location", point)).order_by("driver_id", "-recorded_at").distinct("driver_id")
        candidates = list(online)
        nearest = min((candidate.distance.m for candidate in candidates if candidate.distance), default=None)
        # Round distance to a coarse band so the endpoint cannot be used to track a driver.
        nearest_approx_m = int(round(nearest / 500) * 500) if nearest is not None else None
        return Response({
            "available_drivers": len(candidates),
            "nearest_approx_m": nearest_approx_m,
            "search_radius_m": settings.DRIVER_SEARCH_RADIUS_METERS,
        })
