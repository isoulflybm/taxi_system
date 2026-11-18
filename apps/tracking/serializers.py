from datetime import timedelta

from rest_framework import serializers
from django.utils import timezone


class DriverLocationInputSerializer(serializers.Serializer):
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)
    heading = serializers.IntegerField(min_value=0, max_value=359, required=False, allow_null=True)
    speed_mps = serializers.FloatField(min_value=0, required=False, allow_null=True)
    accuracy_m = serializers.FloatField(min_value=0, required=False, allow_null=True)
    recorded_at = serializers.DateTimeField(required=False)

    def validate_recorded_at(self, value):
        if value > timezone.now() + timedelta(minutes=5):
            raise serializers.ValidationError("Время фиксации не может быть более чем на 5 минут в будущем.")
        return value
