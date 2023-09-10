from django.core.validators import MinValueValidator
from django.db import models


class Payment(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = "Pending"
        PAID = "Paid"

    class TypeChoices(models.TextChoices):
        PAYMENT = "Payment"
        FINE = "Fine"

    status = models.CharField(
        choices=StatusChoices.choices, default="PENDING", max_length=255
    )
    type = models.CharField(
        choices=TypeChoices.choices, default="PAYMENT", max_length=255
    )
    session_url = models.URLField(max_length=400)
    session_id = models.CharField(max_length=255)
    money_to_pay = models.DecimalField(
        max_digits=5, decimal_places=2, validators=[MinValueValidator(0)]
    )

    def __str__(self) -> str:
        return f"{self.type}: {self.status} ({self.money_to_pay}USD)"
