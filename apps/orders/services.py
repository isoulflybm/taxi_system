from datetime import timedelta
from math import asin, cos, radians, sin, sqrt

from django.conf import settings
from django.contrib.gis.measure import D
from django.db import transaction
from django.contrib.gis.db.models.functions import Distance
from django.utils import timezone

from apps.accounts.models import UserProfile
from apps.fleet.models import Vehicle
from apps.tracking.models import DriverLocation
from apps.trips.models import Trip
from apps.tariffs.services import calculate_fare
from apps.geo.services import get_driving_route

from .models import DriverDecline, Order


def build_route_quote(order, tariff):
    route = get_driving_route(order.pickup.x, order.pickup.y, order.dropoff.x, order.dropoff.y)
    order.estimated_distance_m = route["distance_m"]
    order.estimated_duration_s = route["duration_s"]
    order.estimated_price = calculate_fare(tariff, route["distance_m"], route["duration_s"])
    order.currency = tariff.currency
    order.route_geojson = route.get("geometry")
    order.tariff = tariff
    order.tariff_snapshot = {
        "name": tariff.name,
        "base_fare": str(tariff.base_fare),
        "per_km": str(tariff.per_km),
        "per_minute": str(tariff.per_minute),
        "minimum_fare": str(tariff.minimum_fare),
        "currency": tariff.currency,
    }


def _is_busy(profile):
    return Order.objects.filter(
        assigned_driver=profile,
        status__in=(Order.Status.ASSIGNED, Order.Status.DRIVER_ARRIVING, Order.Status.IN_PROGRESS),
    ).exists()


@transaction.atomic
def try_assign_nearest_driver(order):
    """Assign the nearest recently reporting driver with an active, idle vehicle."""
    order = Order.objects.select_for_update().select_related("tariff").get(pk=order.pk)
    if order.assigned_driver_id or order.status != Order.Status.NEW:
        return order

    cutoff = timezone.now() - timedelta(seconds=settings.DRIVER_LOCATION_MAX_AGE_SECONDS)
    latest = list(
        DriverLocation.objects.filter(
            driver__role=UserProfile.Role.DRIVER,
            recorded_at__gte=cutoff,
            location__distance_lte=(order.pickup, D(m=settings.DRIVER_SEARCH_RADIUS_METERS)),
        ).exclude(
            driver_id__in=DriverDecline.objects.filter(order=order).values_list("driver_id", flat=True),
        ).annotate(distance=Distance("location", order.pickup))
        .select_related("driver__user")
        .order_by("driver_id", "-recorded_at")
        .distinct("driver_id")
    )
    latest.sort(key=lambda point: point.distance.m if point.distance else float("inf"))

    for point in latest:
        profile = UserProfile.objects.select_for_update().get(pk=point.driver_id)
        if profile.role != UserProfile.Role.DRIVER or _is_busy(profile):
            continue
        vehicle = Vehicle.objects.filter(driver=profile, state=Vehicle.State.ACTIVE).order_by("pk").first()
        if not vehicle:
            continue
        order.assigned_driver = profile
        order.status = Order.Status.ASSIGNED
        order.assigned_at = timezone.now()
        order.save(update_fields=("assigned_driver", "status", "assigned_at", "updated_at"))
        trip = Trip.objects.select_for_update().filter(order=order).first()
        if trip:
            trip.driver = profile
            trip.vehicle = vehicle
            trip.status = Trip.Status.ASSIGNED
            trip.started_at = None
            trip.finished_at = None
            trip.passenger_picked_up_at = None
            trip.start_position = None
            trip.finish_position = None
            trip.actual_distance_m = None
            trip.final_price = None
            trip.save(update_fields=(
                "driver", "vehicle", "status", "started_at", "finished_at", "passenger_picked_up_at",
                "start_position", "finish_position", "actual_distance_m", "final_price",
            ))
        else:
            Trip.objects.create(order=order, driver=profile, vehicle=vehicle, status=Trip.Status.ASSIGNED)
        return order
    return order


def _haversine_m(a, b):
    lat1, lon1 = radians(a.y), radians(a.x)
    lat2, lon2 = radians(b.y), radians(b.x)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    value = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 6_371_000 * 2 * asin(sqrt(value))


def gps_distance_m(points):
    """Sum sensible GPS segments, ignoring outages and impossible jumps."""
    total = 0.0
    previous = None
    for point in points:
        if point.accuracy_m is not None and point.accuracy_m > 100:
            previous = None
            continue
        if previous:
            seconds = (point.recorded_at - previous.recorded_at).total_seconds()
            if 0 < seconds <= 120:
                distance = _haversine_m(previous.location, point.location)
                if distance / seconds <= 55:  # ignore GPS jumps above 198 km/h
                    total += distance
        previous = point
    return int(round(total))
