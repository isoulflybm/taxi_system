from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.orders.models import Order
from .models import Payment


@transaction.atomic
def record_successful_payment(*, order, amount, method, provider="", provider_reference=""):
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.status != Order.Status.COMPLETED:
        raise ValidationError({"order": "Платёж можно зафиксировать после завершения поездки."})
    due = order.final_price or order.estimated_price
    if due is None:
        raise ValidationError({"amount": "У заказа отсутствует итоговая сумма."})
    paid = sum(
        order.payments.filter(status=Payment.Status.SUCCEEDED).values_list("amount", flat=True),
        Decimal("0.00"),
    )
    try:
        amount = Decimal(str(amount))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValidationError({"amount": "Укажите корректную сумму оплаты."}) from exc
    if not amount.is_finite() or amount <= 0 or paid + amount > due:
        raise ValidationError({"amount": f"Сумма должна быть больше нуля и не превышать остаток {due - paid} KGS."})
    payment = Payment(
        order=order,
        method=method,
        status=Payment.Status.SUCCEEDED,
        amount=amount,
        currency=order.currency,
        provider=provider,
        provider_reference=provider_reference,
        confirmed_at=timezone.now(),
    )
    payment.confirm_success()
    payment.save()
    return payment
