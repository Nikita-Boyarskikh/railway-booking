from django.utils.translation import gettext_lazy as _


class DepartureNotFoundError(Exception):
    """Seat with given number does not found on this train"""

    def __init__(self) -> None:
        super().__init__(_("Departure not found"))


class SeatUnavailableError(Exception):
    """Raised when a requested seat was taken between validation and commit."""

    def __init__(self, car_number: int, seat_number: int) -> None:
        super().__init__(
            _("Seat car={car_number} seat={seat_number} no longer available").format(
                seat_number=seat_number,
                car_number=car_number,
            )
        )
        self.car_number = car_number
        self.seat_number = seat_number


class SeatNotFoundError(Exception):
    """Raised when a seat with given number does not found on given train."""

    def __init__(self, car_number: int, seat_number: int) -> None:
        super().__init__(
            _("Seat car={car_number} seat={seat_number} not found on this train").format(
                car_number=car_number,
                seat_number=seat_number,
            )
        )
