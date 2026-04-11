from datetime import timedelta

from django.db import models
from django.db.models import QuerySet

from apps.trains.models import Train


class Route(models.Model):
    """An ordered chain of :class:`~apps.stations.models.Connection` forming a full path."""

    name = models.CharField(max_length=128)
    price_factor = models.DecimalField(max_digits=6, decimal_places=3, default=1)
    features = models.JSONField(default=dict, blank=True)

    trains: QuerySet[Train]
    route_segments: QuerySet[RouteSegment]

    def __str__(self) -> str:
        return self.name


class RouteSegment(models.Model):
    """A segment's position inside a route with optional stop duration."""

    route = models.ForeignKey(Route, related_name="route_segments", on_delete=models.CASCADE)
    segment = models.ForeignKey("stations.Connection", on_delete=models.PROTECT)
    order = models.PositiveIntegerField()
    stop_duration = models.DurationField(default=timedelta)

    route_id: int
    segment_id: int

    class Meta:
        unique_together = [("route", "segment", "order")]
        ordering = ["order"]
        constraints = [
            # Two segments can never share the same ``order`` within one route.
            # Also powers lookups like ``WHERE route_id = ? ORDER BY order``.
            models.UniqueConstraint(
                fields=["route", "order"], name="routesegment_route_order_uniq"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.route.name} #{self.order} {self.segment}"
