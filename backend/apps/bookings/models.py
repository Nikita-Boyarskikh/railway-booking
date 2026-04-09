import uuid
from decimal import Decimal
from enum import auto

from django.db import models


class Gender(models.TextChoices):
    MALE = auto()
    FEMALE = auto()


class Passenger(models.Model):
    name = models.CharField(max_length=255)
    passport_number = models.CharField(max_length=64)
    gender = models.CharField(max_length=8, choices=Gender.choices)
    birth_date = models.DateField()

    def __str__(self) -> str:
        return self.name


class Order(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    features = models.JSONField(default=dict, blank=True)

    def __str__(self) -> str:
        return f"Order #{self.pk}"


class Booking(models.Model):
    order = models.ForeignKey(Order, related_name="bookings", on_delete=models.CASCADE)
    departure = models.ForeignKey("trains.Departure", on_delete=models.PROTECT)
    seat = models.ForeignKey("trains.Seat", on_delete=models.PROTECT)
    station_from = models.ForeignKey(
        "stations.Station", related_name="bookings_from", on_delete=models.PROTECT
    )
    station_to = models.ForeignKey(
        "stations.Station", related_name="bookings_to", on_delete=models.PROTECT
    )
    passenger = models.ForeignKey(Passenger, on_delete=models.PROTECT)

    def __str__(self) -> str:
        return f"Booking #{self.pk} seat={self.seat_id} dep={self.departure_id}"
