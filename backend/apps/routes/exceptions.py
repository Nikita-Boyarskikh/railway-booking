from django.utils.translation import gettext_lazy as _


class InvalidStationRangeError(Exception):
    """Raised when the station range provided is invalid."""

    def __init__(self) -> None:
        super().__init__(_("Route does not cover the requested station_from → station_to segment"))
