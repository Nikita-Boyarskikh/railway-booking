from typing import TYPE_CHECKING

from django.core.validators import MinValueValidator
from django.db import models
from djmoney.models.fields import MoneyField

if TYPE_CHECKING:
    from django_stubs_ext.db.models.manager import RelatedManager

    from apps.bookings.models import Booking
    from apps.routes.models import RouteSegment


class Station(models.Model):
    """A named station identified in the public API by its short ``code``."""

    name = models.CharField(max_length=128)
    code = models.CharField(max_length=16, unique=True, db_index=True)

    bookings_from: RelatedManager[Booking]
    bookings_to: RelatedManager[Booking]
    connections_out: RelatedManager[Connection]
    connections_in: RelatedManager[Connection]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


class Connection(models.Model):
    """A span of track between two adjacent stations with a base price."""

    station_from = models.ForeignKey(
        Station, related_name="connections_out", on_delete=models.CASCADE
    )
    station_to = models.ForeignKey(Station, related_name="connections_in", on_delete=models.CASCADE)
    distance_km = models.FloatField(validators=[MinValueValidator(0.001)])
    base_price = MoneyField(max_digits=10, decimal_places=2)

    station_from_id: int
    station_to_id: int
    routesegment_set: RelatedManager[RouteSegment]

    def __str__(self) -> str:
        return f"{self.station_from.code}→{self.station_to.code}"
