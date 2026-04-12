from django.utils.translation import gettext_lazy as _

from apps.core.exceptions import RailwayBookingError


class InvalidStationCodeError(RailwayBookingError):
    """Raised when the station is invalid."""

    def __init__(self, code: str):
        super().__init__(_("Invalid station code: {code}").format(code=code))
