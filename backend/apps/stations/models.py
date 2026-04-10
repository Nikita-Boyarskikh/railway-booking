from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import QuerySet

from apps.bookings.models import Booking


class Station(models.Model):
    """A named station identified in the public API by its short ``code``."""

    name = models.CharField(max_length=128)
    code = models.CharField(max_length=16, unique=True, db_index=True)

    bookings_from: QuerySet[Booking]
    bookings_to: QuerySet[Booking]
    segments_out: QuerySet[Segment]
    segments_in: QuerySet[Segment]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


class Segment(models.Model):
    """A span of track between two adjacent stations with a base price."""

    station_from = models.ForeignKey(Station, related_name="segments_out", on_delete=models.CASCADE)
    station_to = models.ForeignKey(Station, related_name="segments_in", on_delete=models.CASCADE)
    distance_km = models.FloatField(validators=[MinValueValidator(0.0)])
    base_price = models.DecimalField(max_digits=10, decimal_places=2)

    station_from_id: int
    station_to_id: int

    def __str__(self) -> str:
        return f"{self.station_from.code}→{self.station_to.code}"
