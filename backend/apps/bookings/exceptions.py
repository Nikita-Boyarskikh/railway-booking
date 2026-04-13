from django.utils.translation import gettext_lazy as _

from apps.core.exceptions import RailwayBookingError


class DepartureNotFoundError(RailwayBookingError):
    """Raised when a requested departure does not found on given train."""

    def __init__(self) -> None:
        super().__init__(_("Departure not found"))


class SeatUnavailableError(RailwayBookingError):
    """Raised when a requested seat does not found on given train."""

    def __init__(self) -> None:
        super().__init__(_("One of requested seats is no longer available"))


class PriceChangedError(RailwayBookingError):
    """Raised when the actual total price differs from the client's expected price."""

    def __init__(self, actual_total: str) -> None:
        self.actual_total = actual_total
        super().__init__(_("Price has changed since you last viewed it"))


class SeatNotFoundError(RailwayBookingError):
    """Raised when a seat with given number does not found on given train."""

    def __init__(self, car_number: int, seat_number: int) -> None:
        super().__init__(
            _("Seat car={car_number} seat={seat_number} not found on this train").format(
                car_number=car_number,
                seat_number=seat_number,
            )
        )
