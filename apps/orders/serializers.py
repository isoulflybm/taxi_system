from django.contrib.gis.geos import Point
from django.db import transaction
from rest_framework import serializers

from .models import Order
from apps.tariffs.models import Tariff
from apps.tariffs.services import resolve_tariff
from apps.geo.services import GeoServiceError
from .services import build_route_quote, try_assign_nearest_driver


class OrderSerializer(serializers.ModelSerializer):
    tariff = serializers.PrimaryKeyRelatedField(queryset=Tariff.objects.filter(is_active=True), required=False, allow_null=True)
    pickup_latitude = serializers.DecimalField(max_digits=9, decimal_places=6, write_only=True)
    pickup_longitude = serializers.DecimalField(max_digits=9, decimal_places=6, write_only=True)
    dropoff_latitude = serializers.DecimalField(max_digits=9, decimal_places=6, write_only=True)
    dropoff_longitude = serializers.DecimalField(max_digits=9, decimal_places=6, write_only=True)
    pickup = serializers.SerializerMethodField()
    dropoff = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()
    client_username = serializers.CharField(source="client.get_username", read_only=True)
    client_phone = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = (
            "id", "pickup_latitude", "pickup_longitude", "dropoff_latitude", "dropoff_longitude",
            "pickup", "dropoff", "pickup_address", "dropoff_address", "status", "estimated_distance_m",
            "estimated_duration_s", "estimated_price", "final_price", "currency", "tariff", "assigned_driver",
            "assigned_at", "created_at", "status_label", "client_username", "client_phone",
        )
        read_only_fields = ("id", "pickup", "dropoff", "status", "estimated_distance_m", "estimated_duration_s", "estimated_price", "final_price", "currency", "assigned_driver", "assigned_at", "created_at")

    def validate_pickup_latitude(self, value):
        if not -90 <= value <= 90:
            raise serializers.ValidationError("Широта должна быть от -90 до 90.")
        return value

    def validate_dropoff_latitude(self, value):
        if not -90 <= value <= 90:
            raise serializers.ValidationError("Широта должна быть от -90 до 90.")
        return value

    def validate_pickup_longitude(self, value):
        if not -180 <= value <= 180:
            raise serializers.ValidationError("Долгота должна быть от -180 до 180.")
        return value

    def validate_dropoff_longitude(self, value):
        if not -180 <= value <= 180:
            raise serializers.ValidationError("Долгота должна быть от -180 до 180.")
        return value

    def create(self, validated_data):
        pickup = Point(float(validated_data.pop("pickup_longitude")), float(validated_data.pop("pickup_latitude")), srid=4326)
        dropoff = Point(float(validated_data.pop("dropoff_longitude")), float(validated_data.pop("dropoff_latitude")), srid=4326)
        tariff = validated_data.pop("tariff", None)
        tariff = resolve_tariff(pickup, tariff)
        if tariff is None:
            raise serializers.ValidationError({"tariff": "Для выбранного адреса нет подходящего активного тарифа."})
        with transaction.atomic():
            order = Order.objects.create(client=self.context["request"].user, pickup=pickup, dropoff=dropoff, tariff=tariff, **validated_data)
            try:
                build_route_quote(order, tariff)
            except GeoServiceError as exc:
                raise serializers.ValidationError({"route": str(exc)}) from exc
            order.save()
            return try_assign_nearest_driver(order)

    def get_pickup(self, obj):
        return {"latitude": obj.pickup.y, "longitude": obj.pickup.x}

    def get_dropoff(self, obj):
        return {"latitude": obj.dropoff.y, "longitude": obj.dropoff.x}

    def get_status_label(self, obj):
        return obj.get_status_display()

    def get_client_phone(self, obj):
        profile = getattr(obj.client, "taxi_profile", None)
        return profile.phone if profile else None
