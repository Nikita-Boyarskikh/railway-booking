from django.utils.translation import gettext_lazy as _

from apps.core.exceptions import RailwayBookingError


class InvalidStationRangeError(RailwayBookingError):
    """Raised when the station range provided is invalid."""

    def __init__(self) -> None:
        super().__init__(_("Route does not cover the requested station_from → station_to path"))
