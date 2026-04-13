from datetime import timedelta
from typing import TYPE_CHECKING

from django.core.validators import MinValueValidator
from django.db import models

if TYPE_CHECKING:
    from django_stubs_ext.db.models.manager import RelatedManager

    from apps.trains.models import Train


class Route(models.Model):
    """An ordered chain of :class:`~apps.stations.models.Connection` forming a full path."""

    name = models.CharField(max_length=128)
    price_factor = models.DecimalField(
        max_digits=6, decimal_places=3, default=1, validators=[MinValueValidator(0)]
    )
    features = models.JSONField(default=dict, blank=True)

    trains: RelatedManager[Train]
    route_segments: RelatedManager[RouteSegment]

    def __str__(self) -> str:
        return self.name


class RouteSegment(models.Model):
    """A connection's position inside a route with optional stop duration."""

    route = models.ForeignKey(Route, related_name="route_segments", on_delete=models.CASCADE)
    connection = models.ForeignKey("stations.Connection", on_delete=models.PROTECT)
    order = models.PositiveIntegerField()
    stop_duration = models.DurationField(default=timedelta)

    route_id: int
    connection_id: int

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["route", "order"], name="routesegment_route_order_uniq"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.route.name} #{self.order} {self.connection}"
