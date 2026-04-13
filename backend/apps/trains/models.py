import uuid
from typing import TYPE_CHECKING

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_stubs_ext.db.models import TypedModelMeta

if TYPE_CHECKING:
    from django_stubs_ext.db.models.manager import RelatedManager


class Train(models.Model):
    """A train assigned to a route, with an average speed and price factor."""

    route = models.ForeignKey("routes.Route", related_name="trains", on_delete=models.PROTECT)
    number = models.CharField(max_length=16, unique=True, db_index=True)
    name = models.CharField(max_length=128, blank=True, default="")
    avg_speed_kmh = models.FloatField(validators=[MinValueValidator(0.1)])
    price_factor = models.DecimalField(
        max_digits=6, decimal_places=3, default=1, validators=[MinValueValidator(0)]
    )
    features = models.JSONField(default=dict, blank=True)

    cars: RelatedManager[Car]
    departures: RelatedManager[Departure]
    route_id: int

    def __str__(self) -> str:
        return f"{self.number} {self.name}".strip()


class CarType(models.TextChoices):
    """Predefined types of cars, used for filtering and default pricing/features."""

    COMMON = "common", _("Common")
    SLEEPER = "sleeper", _("Sleeper")
    LUXURY = "luxury", _("Luxury")
    DINING = "dining", _("Dining")
    OTHER = "other", _("Other")


class Car(models.Model):
    """A wagon within a train, containing numbered seats."""

    train = models.ForeignKey(Train, related_name="cars", on_delete=models.CASCADE)
    number = models.PositiveIntegerField(verbose_name=_("Car number"))
    car_type = models.CharField(max_length=32, default=CarType.COMMON, choices=CarType.choices)
    features = models.JSONField(default=dict, blank=True)
    price_factor = models.DecimalField(
        max_digits=6, decimal_places=3, default=1, validators=[MinValueValidator(0)]
    )

    seats: RelatedManager[Seat]
    train_id: int

    class Meta(TypedModelMeta):
        ordering = ["number"]
        constraints = [
            models.UniqueConstraint(fields=["train", "number"], name="car_train_number_uniq"),
        ]

    def __str__(self) -> str:
        return f"{self.train.number}/car{self.number}"


class SeatType(models.TextChoices):
    """Predefined types of seats, used for filtering and default pricing/features."""

    COMMON = "common", _("Common")
    VIP = "vip", _("VIP")
    SLEEPER = "sleeper", _("Sleeper")
    OTHER = "other", _("Other")


class Seat(models.Model):
    """A single seat inside a car, identified publicly by ``(car, number)``."""

    car = models.ForeignKey(Car, related_name="seats", on_delete=models.CASCADE)
    number = models.PositiveIntegerField()
    seat_type = models.CharField(max_length=32, default=SeatType.COMMON, choices=SeatType.choices)
    price_factor = models.DecimalField(
        max_digits=6, decimal_places=3, default=1, validators=[MinValueValidator(0)]
    )

    car_id: int

    class Meta(TypedModelMeta):
        ordering = ["number"]
        constraints = [
            models.UniqueConstraint(fields=["car", "number"], name="seat_car_number_uniq"),
        ]

    def __str__(self) -> str:
        return f"{self.car}/seat{self.number}"


class Departure(models.Model):
    """A specific run of a :class:`Train` on a given date and start time."""

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    train = models.ForeignKey(Train, related_name="departures", on_delete=models.CASCADE)
    date = models.DateField()
    departure_time = models.TimeField()

    train_id: int

    class Meta(TypedModelMeta):
        ordering = ["date", "departure_time"]
        indexes = [
            # search_departures filters by date; composite with train_id speeds
            # the join onto train/route during the same query.
            models.Index(fields=["date", "train"]),
        ]

    def __str__(self) -> str:
        return f"{self.train.number} on {self.date} @ {self.departure_time}"
