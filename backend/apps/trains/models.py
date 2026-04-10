import uuid
from decimal import Decimal

from django.db import models


class Train(models.Model):
    """A train assigned to a route, with an average speed and price factor."""

    route = models.ForeignKey("routes.Route", related_name="trains", on_delete=models.PROTECT)
    number = models.CharField(max_length=16, unique=True, db_index=True)
    name = models.CharField(max_length=128, blank=True, default="")
    avg_speed_kmh = models.DecimalField(max_digits=6, decimal_places=2)
    price_factor = models.DecimalField(max_digits=6, decimal_places=3, default=Decimal("1.0"))
    features = models.JSONField(default=dict, blank=True)

    def __str__(self) -> str:
        return f"{self.number} {self.name}".strip()


class Car(models.Model):
    """A wagon within a train, containing numbered seats."""

    train = models.ForeignKey(Train, related_name="cars", on_delete=models.CASCADE)
    number = models.PositiveIntegerField()
    car_type = models.CharField(max_length=32, default="common")
    features = models.JSONField(default=dict, blank=True)
    price_factor = models.DecimalField(max_digits=6, decimal_places=3, default=Decimal("1.0"))

    class Meta:
        unique_together = [("train", "number")]
        ordering = ["number"]

    def __str__(self) -> str:
        return f"{self.train.number}/car{self.number}"


class Seat(models.Model):
    """A single seat inside a car, identified publicly by ``(car, number)``."""

    car = models.ForeignKey(Car, related_name="seats", on_delete=models.CASCADE)
    number = models.PositiveIntegerField()
    seat_type = models.CharField(max_length=32, default="common")
    price_factor = models.DecimalField(max_digits=6, decimal_places=3, default=Decimal("1.0"))

    class Meta:
        unique_together = [("car", "number")]
        ordering = ["number"]

    def __str__(self) -> str:
        return f"{self.car}/seat{self.number}"


class Departure(models.Model):
    """A specific run of a :class:`Train` on a given date and start time."""

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    train = models.ForeignKey(Train, related_name="departures", on_delete=models.CASCADE)
    date = models.DateField()
    departure_time = models.TimeField()

    class Meta:
        ordering = ["date", "departure_time"]

    def __str__(self) -> str:
        return f"{self.train.number} on {self.date} @ {self.departure_time}"
