from django.db import models


class Station(models.Model):
    name = models.CharField(max_length=128)
    code = models.CharField(max_length=16, unique=True, db_index=True)

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


class Segment(models.Model):
    station_from = models.ForeignKey(Station, related_name="segments_out", on_delete=models.CASCADE)
    station_to = models.ForeignKey(Station, related_name="segments_in", on_delete=models.CASCADE)
    distance_km = models.DecimalField(max_digits=8, decimal_places=2)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self) -> str:
        return f"{self.station_from.code}→{self.station_to.code}"
