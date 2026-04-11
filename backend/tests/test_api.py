"""HTTP API tests — one test per endpoint/scenario."""

from typing import Any
from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from apps.stations.models import Station
from apps.trains.models import Car, Departure, Seat


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


# ---------------------------------------------------------------------------
# GET /api/stations/
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_stations_list(api_client: APIClient, stations: list[Station]) -> None:
    r = api_client.get("/api/stations/")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 4
    assert all("name" in s and "code" in s for s in data)
    # no integer PKs exposed
    assert all("id" not in s for s in data)


@pytest.mark.django_db
def test_stations_list_sorted_by_name(api_client: APIClient, stations: list[Station]) -> None:
    r = api_client.get("/api/stations/")
    names = [s["name"] for s in r.json()]
    assert names == sorted(names)


# ---------------------------------------------------------------------------
# GET /api/departures/?from=&to=&date=
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_departures_search(
    api_client: APIClient,
    stations: list[Station],
    seat: Seat,
    seat2: Seat,
    departure: Departure,
) -> None:
    r = api_client.get(
        f"/api/departures/?from={stations[0].code}&to={stations[3].code}&date=2026-05-01"
    )
    assert r.status_code == 200
    deps = r.json()
    assert len(deps) == 1
    assert deps[0]["uuid"] == str(departure.uuid)
    assert deps[0]["free_seat_count"] == 2


@pytest.mark.django_db
def test_departures_search_missing_params(api_client: APIClient) -> None:
    r = api_client.get("/api/departures/")
    assert r.status_code == 400


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_departures_search_no_results(
    api_client: APIClient,
    stations: list[Station],
    departure: Departure,
) -> None:
    r = api_client.get(
        f"/api/departures/?from={stations[0].code}&to={stations[3].code}&date=2099-01-01"
    )
    assert r.status_code == 200
    assert r.json() == []


# ---------------------------------------------------------------------------
# GET /api/departures/{uuid}/seats/?from=&to=
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_seats_view(
    api_client: APIClient,
    stations: list[Station],
    seat: Seat,
    seat2: Seat,
    departure: Departure,
) -> None:
    r = api_client.get(
        f"/api/departures/{departure.uuid}/seats/?from={stations[0].code}&to={stations[3].code}"
    )
    assert r.status_code == 200
    cars = r.json()["cars"]
    assert len(cars) == 1
    assert len(cars[0]["seats"]) == 2
    # Check schema: each seat has expected keys
    for s in cars[0]["seats"]:
        assert set(s.keys()) >= {"number", "seat_type", "status", "price"}
        assert s["status"] in ("free", "occupied")


@pytest.mark.django_db
def test_seats_view_departure_not_found(api_client: APIClient, stations: list[Station]) -> None:
    r = api_client.get(
        f"/api/departures/{uuid4()}/seats/?from={stations[0].code}&to={stations[3].code}"
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/orders/
# ---------------------------------------------------------------------------


def _order_payload(
    departure: Departure,
    stations: list[Station],
    car: Car,
    seat: Seat,
) -> dict[str, Any]:
    return {
        "departure_uuid": str(departure.uuid),
        "station_from_code": stations[0].code,
        "station_to_code": stations[3].code,
        "items": [
            {
                "car_number": car.number,
                "seat_number": seat.number,
                "passenger_name": "Jane",
                "passenger_passport": "X1",
                "passenger_gender": "female",
                "passenger_birth_date": "1985-06-01",
            }
        ],
    }


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_order_create(
    api_client: APIClient,
    stations: list[Station],
    car: Car,
    seat: Seat,
    departure: Departure,
) -> None:
    r = api_client.post(
        "/api/orders/",
        _order_payload(departure, stations, car, seat),
        format="json",
    )
    assert r.status_code == 201
    data = r.json()
    assert "uuid" in data
    assert "total_price" in data
    assert "bookings" in data
    assert len(data["bookings"]) == 1
    # No integer PKs exposed
    assert "id" not in data
    booking = data["bookings"][0]
    assert "id" not in booking
    assert booking["car_number"] == car.number
    assert booking["seat_number"] == seat.number


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_order_create_conflict_409(
    api_client: APIClient,
    stations: list[Station],
    car: Car,
    seat: Seat,
    departure: Departure,
) -> None:
    payload = _order_payload(departure, stations, car, seat)
    api_client.post("/api/orders/", payload, format="json")
    r2 = api_client.post("/api/orders/", payload, format="json")
    assert r2.status_code == 409
    body = r2.json()
    assert "detail" in body
    assert body["car_number"] == car.number
    assert body["seat_number"] == seat.number


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_order_create_missing_field_400(api_client: APIClient) -> None:
    r = api_client.post("/api/orders/", {}, format="json")
    assert r.status_code == 400


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_order_create_empty_items_400(
    api_client: APIClient,
    stations: list[Station],
    departure: Departure,
) -> None:
    """Serializer rejects empty items list."""
    r = api_client.post(
        "/api/orders/",
        {
            "departure_uuid": str(departure.uuid),
            "station_from_code": stations[0].code,
            "station_to_code": stations[3].code,
            "items": [],
        },
        format="json",
    )
    assert r.status_code == 400
    assert "items" in r.json()


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_order_create_same_station_400(
    api_client: APIClient,
    stations: list[Station],
    car: Car,
    seat: Seat,
    departure: Departure,
) -> None:
    """Serializer rejects from == to."""
    payload = _order_payload(departure, stations, car, seat)
    payload["station_to_code"] = payload["station_from_code"]
    r = api_client.post("/api/orders/", payload, format="json")
    assert r.status_code == 400


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_order_create_invalid_gender_400(
    api_client: APIClient,
    stations: list[Station],
    car: Car,
    seat: Seat,
    departure: Departure,
) -> None:
    """Serializer rejects invalid gender choice."""
    payload = _order_payload(departure, stations, car, seat)
    payload["items"][0]["passenger_gender"] = "invalid"
    r = api_client.post("/api/orders/", payload, format="json")
    assert r.status_code == 400


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_order_create_wrong_departure_uuid_400(
    api_client: APIClient,
    stations: list[Station],
    car: Car,
    seat: Seat,
    departure: Departure,
) -> None:
    """Serializer rejects invalid gender choice."""
    payload = _order_payload(departure, stations, car, seat)
    payload["departure_uuid"] = uuid4()
    r = api_client.post("/api/orders/", payload, format="json")
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# GET /api/orders/{uuid}/
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_order_retrieve(
    api_client: APIClient,
    stations: list[Station],
    car: Car,
    seat: Seat,
    departure: Departure,
) -> None:
    r = api_client.post(
        "/api/orders/",
        _order_payload(departure, stations, car, seat),
        format="json",
    )
    order_uuid = r.json()["uuid"]
    r2 = api_client.get(f"/api/orders/{order_uuid}/")
    assert r2.status_code == 200
    assert r2.json()["uuid"] == order_uuid


@pytest.mark.django_db
def test_order_retrieve_not_found(api_client: APIClient) -> None:
    r = api_client.get(f"/api/orders/{uuid4()}/")
    assert r.status_code == 404
