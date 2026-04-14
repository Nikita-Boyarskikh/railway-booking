import uuid
from typing import TYPE_CHECKING

from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import IntegerRangeField, RangeOperators
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator, RegexValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from djmoney.models.fields import MoneyField
from psycopg.types.range import Range

if TYPE_CHECKING:
    import datetime
    from collections.abc import Iterable

    from django.db.models.base import ModelBase
    from django_stubs_ext.db.models.manager import RelatedManager

BOOKING_NO_OVERLAP_CONSTRAINT = "booking_no_seat_overlap"


def validate_past_date(value: datetime.date) -> None:
    """Reject birth dates that are today or in the future."""
    if value >= timezone.localdate():
        raise ValidationError(_("Birth date must be in the past."), code="birth_date_not_past")


class Gender(models.TextChoices):
    """Passenger gender choices."""

    MALE = "male", _("Male")
    FEMALE = "female", _("Female")


class Passenger(models.Model):
    """A person travelling on one booking (name, passport, gender, DOB)."""

    name = models.CharField(max_length=255)
    passport_number = models.CharField(
        max_length=64,
        validators=[
            MinLengthValidator(4),
            RegexValidator(
                regex=r"^[A-Za-z0-9 -]+$",
                message=_("Passport number may only contain letters, digits, spaces, and dashes."),
                code="passport_number_invalid",
            ),
        ],
    )
    gender = models.CharField(max_length=8, choices=Gender.choices)
    birth_date = models.DateField(validators=[validate_past_date])

    def __str__(self) -> str:
        return self.name


class Order(models.Model):
    """A customer order grouping one or more bookings for a single departure."""

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    total_price = MoneyField(max_digits=12, decimal_places=2, default=0)
    features = models.JSONField(default=dict, blank=True)

    bookings: RelatedManager[Booking]

    def __str__(self) -> str:
        return _("Order #{uuid}").format(uuid=self.uuid)


class Booking(models.Model):
    """One seat reserved on one departure for one boarding→alighting range."""

    order = models.ForeignKey(Order, related_name="bookings", on_delete=models.CASCADE)
    departure = models.ForeignKey("trains.Departure", on_delete=models.PROTECT)
    seat = models.ForeignKey("trains.Seat", on_delete=models.PROTECT)
    station_from = models.ForeignKey(
        "stations.Station", related_name="bookings_from", on_delete=models.PROTECT
    )
    station_to = models.ForeignKey(
        "stations.Station", related_name="bookings_to", on_delete=models.PROTECT
    )
    passenger = models.ForeignKey(Passenger, on_delete=models.PROTECT)
    # Half-open range ``[from_order, to_order)`` over the train route's
    # RouteSegment.order.  Auto-computed from ``(station_from, station_to)``
    # in :meth:`save` (and :meth:`clean` for admin forms).  The exclusion
    # constraint below enforces no-overlap at the DB level.
    segment_range = IntegerRangeField(blank=True)

    order_id: int
    departure_id: int
    seat_id: int
    station_from_id: int
    station_to_id: int
    passenger_id: int

    class Meta:
        indexes = [
            # Hot path: free_seat_ids filter by (departure, seat).
            models.Index(fields=("departure", "seat")),
        ]
        constraints = [
            ExclusionConstraint(
                name=BOOKING_NO_OVERLAP_CONSTRAINT,
                expressions=[
                    ("departure", RangeOperators.EQUAL),
                    ("seat", RangeOperators.EQUAL),
                    ("segment_range", RangeOperators.OVERLAPS),
                ],
            ),
        ]

    def __str__(self) -> str:
        return _(
            "Booking {train_number} {station_from}→{station_to} car={car_number} seat={seat_number}"
        ).format(
            train_number=self.departure.train.number,
            station_from=self.station_from.code,
            station_to=self.station_to.code,
            car_number=self.seat.car.number,
            seat_number=self.seat.number,
        )

    def save(
        self,
        *,
        force_insert: bool | tuple[ModelBase, ...] = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: Iterable[str] | None = None,
    ) -> None:
        self.compute_segment_range()
        super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )

    def clean(self) -> None:
        """Cross-field integrity checks (called by admin forms and full_clean)."""
        from apps.routes.exceptions import InvalidStationRangeError

        errors: dict[str, list[ValidationError]] = {}

        # All FK ids must be set before we can cross-check.
        if not (
            self.departure_id and self.seat_id and self.station_from_id and self.station_to_id
        ):  # pragma: no cover
            return

        # 1. Seat must belong to the departure's train.
        if self.seat.car.train_id != self.departure.train_id:
            errors.setdefault("seat", []).append(
                ValidationError(
                    _("Seat does not belong to the departure's train."),
                    code="seat_wrong_train",
                )
            )

        # 2. Both stations must be on the route, in the correct direction.
        #    Also auto-compute segment_range.
        try:
            self.compute_segment_range()
        except InvalidStationRangeError:
            errors.setdefault("station_from", []).append(
                ValidationError(
                    _("Stations are not on this route or are in the wrong order."),
                    code="invalid_station_range",
                )
            )

        if errors:
            raise ValidationError(errors)

    @staticmethod
    def make_segment_range(from_order: int, to_order: int) -> Range[int]:
        """Build a half-open ``[from_order, to_order)`` range for segment overlap checks."""
        return Range(from_order, to_order, bounds="[)")

    def compute_segment_range(self) -> None:
        """Derive ``segment_range`` from the departure's route and station pair.

        Called automatically by :meth:`save`.  For ``bulk_create`` (which
        skips ``save``), call this on each instance before passing them.
        """
        from apps.routes.services import resolve_station_range

        route = self.departure.train.route
        from_order, to_order = resolve_station_range(
            route, self.station_from_id, self.station_to_id
        )
        self.segment_range = self.make_segment_range(from_order, to_order)
