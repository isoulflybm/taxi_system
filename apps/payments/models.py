from decimal import Decimal, ROUND_HALF_UP

from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class PlatformSettings(models.Model):
    commission_percent = models.DecimalField(
        "Комиссия сервиса, %", max_digits=5, decimal_places=2, default=Decimal("0.00"),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Настройки комиссии"
        verbose_name_plural = "Настройки комиссии"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f"Комиссия сервиса: {self.commission_percent}%"


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = "cash", "Наличные"
        CARD = "card", "Карта"
        WALLET = "wallet", "Электронный кошелёк"
        MANUAL = "manual", "Внесён вручную"

    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает подтверждения"
        SUCCEEDED = "succeeded", "Успешно оплачен"
        FAILED = "failed", "Ошибка оплаты"
        REFUNDED = "refunded", "Возврат"

    order = models.ForeignKey("orders.Order", on_delete=models.PROTECT, related_name="payments")
    method = models.CharField(max_length=16, choices=Method.choices, default=Method.CASH)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    currency = models.CharField(max_length=3, default="KGS")
    commission_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    driver_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    provider = models.CharField(max_length=64, blank=True)
    provider_reference = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def confirm_success(self):
        settings = PlatformSettings.get_solo()
        self.commission_percent = settings.commission_percent
        self.commission_amount = (self.amount * self.commission_percent / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        self.driver_amount = self.amount - self.commission_amount

    def __str__(self):
        return f"{self.amount} {self.currency} · {self.get_status_display()} · {self.order_id}"
