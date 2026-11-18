from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import UserProfile
from .models import DriverDecline, Order
from .serializers import OrderSerializer
from .services import gps_distance_m, try_assign_nearest_driver
from apps.tracking.models import DriverLocation
from apps.trips.models import Trip
from apps.tariffs.services import calculate_fare_from_rates
from apps.payments.models import Payment
from apps.payments.services import record_successful_payment


class OrderViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = OrderSerializer
    permission_classes = (IsAuthenticated,)
    http_method_names = ("get", "post", "head", "options")

    def get_queryset(self):
        user = self.request.user
        profile = getattr(user, "taxi_profile", None)
        if user.is_staff or (profile and profile.role in (UserProfile.Role.DISPATCHER, UserProfile.Role.ADMIN)):
            return Order.objects.select_related("client", "client__taxi_profile", "assigned_driver", "tariff", "service_zone")
        if profile and profile.role == UserProfile.Role.DRIVER:
            return Order.objects.filter(assigned_driver=profile).select_related("client", "client__taxi_profile", "tariff", "service_zone")
        return Order.objects.filter(client=user).select_related("client__taxi_profile", "assigned_driver", "tariff", "service_zone")

    def create(self, request, *args, **kwargs):
        profile = getattr(request.user, "taxi_profile", None)
        if not request.user.is_staff and profile and profile.role not in (UserProfile.Role.CUSTOMER, UserProfile.Role.DISPATCHER):
            raise PermissionDenied("Создавать заказ может клиент или диспетчер.")
        return super().create(request, *args, **kwargs)

    def _require_driver(self, order):
        profile = getattr(self.request.user, "taxi_profile", None)
        if not profile or profile.role != UserProfile.Role.DRIVER or order.assigned_driver_id != profile.pk:
            raise PermissionDenied("Это действие доступно только назначенному водителю.")
        return profile

    @action(detail=True, methods=("post",), url_path="driver-arriving")
    def driver_arriving(self, request, pk=None):
        order = self.get_object()
        self._require_driver(order)
        if order.status != Order.Status.ASSIGNED:
            raise ValidationError({"status": "Заказ нельзя перевести в этот статус."})
        order.status = Order.Status.DRIVER_ARRIVING
        order.save(update_fields=("status", "updated_at"))
        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=("post",))
    def decline(self, request, pk=None):
        order = self.get_object()
        profile = self._require_driver(order)
        if order.status not in (Order.Status.ASSIGNED, Order.Status.DRIVER_ARRIVING):
            raise ValidationError({"status": "Отказаться можно до начала поездки."})
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=order.pk)
            if order.assigned_driver_id != profile.pk or order.status not in (Order.Status.ASSIGNED, Order.Status.DRIVER_ARRIVING):
                raise ValidationError({"status": "Заказ уже изменён или передан другому водителю."})
            DriverDecline.objects.get_or_create(
                order=order,
                driver=profile,
                defaults={"reason": str(request.data.get("reason", ""))[:255]},
            )
            trip = Trip.objects.select_for_update().filter(order=order).first()
            if trip:
                trip.status = Trip.Status.CANCELLED
                trip.finished_at = timezone.now()
                trip.save(update_fields=("status", "finished_at"))
            order.assigned_driver = None
            order.assigned_at = None
            order.status = Order.Status.NEW
            order.save(update_fields=("assigned_driver", "assigned_at", "status", "updated_at"))
        order = try_assign_nearest_driver(order)
        return Response({
            "order": self.get_serializer(order).data,
            "reassigned": bool(order.assigned_driver_id),
            "detail": "Заказ передан следующему водителю." if order.assigned_driver_id else "Заказ снят с вас и вернулся в очередь поиска водителя.",
        })

    @action(detail=True, methods=("post",))
    def start(self, request, pk=None):
        order = self.get_object()
        self._require_driver(order)
        if order.status not in (Order.Status.ASSIGNED, Order.Status.DRIVER_ARRIVING):
            raise ValidationError({"status": "Начать можно только назначенный заказ."})
        with transaction.atomic():
            trip = Trip.objects.select_for_update().get(order=order)
            trip.status = Trip.Status.ACTIVE
            trip.started_at = timezone.now()
            location = DriverLocation.objects.filter(driver=trip.driver).order_by("-recorded_at").first()
            if location:
                trip.start_position = location.location
            trip.save(update_fields=("status", "started_at", "start_position"))
            order.status = Order.Status.IN_PROGRESS
            order.save(update_fields=("status", "updated_at"))
        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=("post",))
    def complete(self, request, pk=None):
        order = self.get_object()
        self._require_driver(order)
        if order.status != Order.Status.IN_PROGRESS:
            raise ValidationError({"status": "Завершить можно только начатую поездку."})
        with transaction.atomic():
            trip = Trip.objects.select_for_update().select_related("order").get(order=order)
            if not trip.started_at:
                raise ValidationError({"trip": "У поездки отсутствует время начала."})
            points = list(DriverLocation.objects.filter(
                driver=trip.driver, recorded_at__gte=trip.started_at,
            ).order_by("recorded_at")[:5000])
            actual_distance = gps_distance_m(points)
            # Fall back to the road-network estimate if the device did not send enough GPS points.
            billable_distance = actual_distance or order.estimated_distance_m or 0
            elapsed_s = max(0, int((timezone.now() - trip.started_at).total_seconds()))
            snapshot = order.tariff_snapshot or {}
            try:
                base = Decimal(snapshot["base_fare"])
                per_km = Decimal(snapshot["per_km"])
                per_minute = Decimal(snapshot["per_minute"])
                minimum = Decimal(snapshot["minimum_fare"])
                final_price = calculate_fare_from_rates(base, per_km, per_minute, minimum, billable_distance, elapsed_s)
            except (KeyError, TypeError, ValueError):
                final_price = order.estimated_price
            finished = timezone.now()
            latest = points[-1] if points else None
            trip.status = Trip.Status.COMPLETED
            trip.finished_at = finished
            trip.finish_position = latest.location if latest else None
            trip.actual_distance_m = actual_distance or None
            trip.final_price = final_price
            trip.save(update_fields=("status", "finished_at", "finish_position", "actual_distance_m", "final_price"))
            order.status = Order.Status.COMPLETED
            order.final_price = final_price
            order.save(update_fields=("status", "final_price", "updated_at"))
        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=("post",))
    def cancel(self, request, pk=None):
        order = self.get_object()
        profile = getattr(request.user, "taxi_profile", None)
        dispatcher = request.user.is_staff or (profile and profile.role in (UserProfile.Role.DISPATCHER, UserProfile.Role.ADMIN))
        client = order.client_id == request.user.pk
        if not (dispatcher or client):
            raise PermissionDenied("Водитель передаёт заказ следующему через действие «Отказаться».")
        if order.status in (Order.Status.IN_PROGRESS, Order.Status.COMPLETED, Order.Status.CANCELLED):
            raise ValidationError({"status": "Текущий статус не позволяет отменить заказ."})
        with transaction.atomic():
            order.status = Order.Status.CANCELLED
            order.cancelled_at = timezone.now()
            order.save(update_fields=("status", "cancelled_at", "updated_at"))
            if hasattr(order, "trip"):
                order.trip.status = Trip.Status.CANCELLED
                order.trip.finished_at = timezone.now()
                order.trip.save(update_fields=("status", "finished_at"))
        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=("post",), permission_classes=(IsAuthenticated,))
    def retry_assignment(self, request, pk=None):
        profile = getattr(request.user, "taxi_profile", None)
        if not (request.user.is_staff or (profile and profile.role in (UserProfile.Role.DISPATCHER, UserProfile.Role.ADMIN))):
            raise PermissionDenied("Повторное назначение доступно диспетчеру.")
        order = self.get_object()
        if order.status != Order.Status.NEW:
            raise ValidationError({"status": "Повторное назначение доступно только для нового заказа."})
        order = try_assign_nearest_driver(order)
        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=("post",), url_path="payments/record")
    def record_payment(self, request, pk=None):
        profile = getattr(request.user, "taxi_profile", None)
        if not (request.user.is_staff or (profile and profile.role in (UserProfile.Role.DISPATCHER, UserProfile.Role.ADMIN))):
            raise PermissionDenied("Фиксировать оплату может диспетчер.")
        order = self.get_object()
        amount = request.data.get("amount")
        method = request.data.get("method", Payment.Method.CASH)
        if method not in Payment.Method.values:
            raise ValidationError({"method": "Неизвестный способ оплаты."})
        payment = record_successful_payment(
            order=order,
            amount=amount,
            method=method,
            provider=str(request.data.get("provider", ""))[:64],
            provider_reference=str(request.data.get("provider_reference", ""))[:128],
        )
        return Response({
            "id": payment.pk,
            "status": payment.status,
            "amount": str(payment.amount),
            "currency": payment.currency,
            "commission_percent": str(payment.commission_percent),
            "commission_amount": str(payment.commission_amount),
            "driver_amount": str(payment.driver_amount),
        }, status=status.HTTP_201_CREATED)
