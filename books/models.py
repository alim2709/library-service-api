from django.core.validators import MinValueValidator
from django.db import models


class Book(models.Model):
    class CoverChoices(models.TextChoices):
        HARD = ("Hard",)
        SOFT = "Soft"

    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    cover = models.CharField(choices=CoverChoices.choices, default="SOFT", max_length=255)
    inventory = models.PositiveIntegerField()
    daily_fee = models.DecimalField(
        max_digits=5, decimal_places=2, validators=[MinValueValidator(0)]
    )

    class Meta:
        ordering = ("title",)

    def __str__(self):
        return self.title
