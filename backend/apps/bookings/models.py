import uuid

from django.db import models
from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _
from djmoney.models.fields import MoneyField


class Gender(models.TextChoices):
    """Passenger gender choices."""

    MALE = "male", _("Male")
    FEMALE = "female", _("Female")


class Passenger(models.Model):
    """A person travelling on one booking (name, passport, gender, DOB)."""

    name = models.CharField(max_length=255)
    passport_number = models.CharField(max_length=64)
    gender = models.CharField(max_length=8, choices=Gender.choices)
    birth_date = models.DateField()

    def __str__(self) -> str:
        return self.name


class Order(models.Model):
    """A customer order grouping one or more bookings for a single departure."""

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    total_price = MoneyField(max_digits=12, decimal_places=2, default=0)
    features = models.JSONField(default=dict, blank=True)

    bookings: QuerySet[Booking]

    def __str__(self) -> str:
        return _("Order #{uuid}").format(uuid=self.uuid)


class Booking(models.Model):
    """One seat reserved on one departure for one boarding→alighting range."""

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

    order_id: int
    departure_id: int
    seat_id: int
    station_from_id: int
    station_to_id: int
    passenger_id: int

    def __str__(self) -> str:
        return _("Booking {train_number} {station_from}→{station_to} car={car_number} seat={seat_number}").format(
            train_number=self.departure.train.number,
            station_from=self.station_from.code,
            station_to=self.station_to.code,
            car_number=self.seat.car.number,
            seat_number=self.seat.number,
        )
