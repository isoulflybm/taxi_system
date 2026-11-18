from decimal import Decimal, ROUND_HALF_UP

from .models import Tariff


def resolve_tariff(point, requested=None):
    if requested is not None:
        if requested.zone_id and not requested.zone.boundary.contains(point):
            return None
        return requested
    zonal = Tariff.objects.filter(is_active=True, zone__boundary__contains=point).order_by("pk").first()
    return zonal or Tariff.objects.filter(is_active=True, zone__isnull=True).order_by("pk").first()


def calculate_fare(tariff, distance_m: int, duration_s: int) -> Decimal:
    """Calculate a quote from trusted route-engine distance/time, in tariff currency."""
    return calculate_fare_from_rates(
        tariff.base_fare, tariff.per_km, tariff.per_minute,
        tariff.minimum_fare, distance_m, duration_s,
    )


def calculate_fare_from_rates(base_fare, per_km, per_minute, minimum_fare, distance_m: int, duration_s: int) -> Decimal:
    if distance_m < 0 or duration_s < 0:
        raise ValueError("Distance and duration must not be negative")
    distance_km = Decimal(distance_m) / Decimal(1000)
    duration_min = Decimal(duration_s) / Decimal(60)
    amount = Decimal(base_fare) + Decimal(per_km) * distance_km + Decimal(per_minute) * duration_min
    amount = max(amount, Decimal(minimum_fare))
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
