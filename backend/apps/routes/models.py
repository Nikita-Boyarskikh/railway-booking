from datetime import timedelta
from decimal import Decimal

from django.db import models


class Route(models.Model):
    name = models.CharField(max_length=128)
    price_factor = models.DecimalField(max_digits=6, decimal_places=3, default=Decimal("1.0"))
    features = models.JSONField(default=dict, blank=True)

    def __str__(self) -> str:
        return self.name


class RouteSegment(models.Model):
    route = models.ForeignKey(Route, related_name="route_segments", on_delete=models.CASCADE)
    segment = models.ForeignKey("stations.Segment", on_delete=models.PROTECT)
    order = models.PositiveIntegerField()
    stop_duration = models.DurationField(default=timedelta)

    class Meta:
        unique_together = [("route", "segment", "order")]
        ordering = ["order"]

    def __str__(self) -> str:
        return f"{self.route.name} #{self.order} {self.segment}"
