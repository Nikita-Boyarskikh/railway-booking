from decimal import Decimal

from django.db import models


class Config(models.Model):
    """Singleton config row (pk=1)."""

    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))

    class Meta:
        verbose_name = "Configuration"

    def __str__(self) -> str:
        return f"Config(base_price={self.base_price})"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls) -> Config:
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
