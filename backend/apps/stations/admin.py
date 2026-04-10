from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Connection, Station


@admin.register(Connection)
class ConnectionAdmin(admin.ModelAdmin[Connection]):
    """Admin for :class:`Connection`"""
    list_display = ("from_to", "station_from", "station_to", "distance_km", "base_price")
    ordering = ("station_from__code", "station_to__code")
    search_fields = ("station_from__code", "station_from__name", "station_to__code", "station_to__name")
    readonly_fields = ("from_to",)

    @admin.display(description=_("From → To"))
    def from_to(self, obj: Connection) -> str:
        return f"{obj.station_from.code} → {obj.station_to.code}"


@admin.register(Station)
class StationAdmin(admin.ModelAdmin[Station]):
    """Admin for :class:`Station`"""
    list_display = ("code", "name")
    ordering = ("code",)
    search_fields = ("code", "name")
