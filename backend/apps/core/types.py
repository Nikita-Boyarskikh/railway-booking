"""Shared TypedDict definitions for service-layer return types."""

from typing import Any, TypedDict


class TimetableStop(TypedDict):
    """One stop in the timetable returned by ``compute_timetable``."""

    station_id: int
    arrival_time: str | None
    departure_time: str | None


class DepartureSummary(TypedDict):
    """Single departure row from ``search_departures``."""

    uuid: str
    train_number: str
    train_name: str
    departure_time: str | None
    arrival_time: str | None
    free_seat_count: int
    min_price: str | None


class SeatDict(TypedDict):
    """Per-seat payload inside a :class:`CarDict`."""

    number: int
    seat_type: str
    status: str  # "free" | "occupied"
    price: str


class CarDict(TypedDict):
    """Per-car payload in the ``list_seats`` response."""

    number: int
    car_type: str
    features: dict[str, Any]
    seats: list[SeatDict]


class SeatsResponse(TypedDict):
    """Top-level response from ``list_seats``."""

    cars: list[CarDict]


class OrderItemInput(TypedDict):
    """Expected shape of each element in the ``items`` list for ``create_order``."""

    car_number: int
    seat_number: int
    passenger_name: str
    passenger_passport: str
    passenger_gender: str
    passenger_birth_date: str
