"""HTTP API tests — one test per endpoint/scenario."""

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from django.conf import settings
from rest_framework.test import APIClient

from tests.conftest import create_order_payload, make_order_item

if TYPE_CHECKING:
    from apps.bookings.models import Passenger
    from apps.stations.models import Station
    from apps.trains.models import Car, Departure, Seat


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


# ---------------------------------------------------------------------------
# GET /api/v1/stations/
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_stations_list(
    api_client: APIClient,
    station_a: Station,
    station_b: Station,
    station_c: Station,
    station_d: Station,
) -> None:
    r = api_client.get(f"/api/v{settings.API_VERSION}/stations/")
    assert r.status_code == 200, r.json()
    data = r.json()
    assert len(data) == 4
    assert all("name" in s and "code" in s for s in data)
    # no integer PKs exposed
    assert all("id" not in s for s in data)


@pytest.mark.django_db
def test_stations_list_sorted_by_name(
    api_client: APIClient,
    station_a: Station,
    station_b: Station,
    station_c: Station,
    station_d: Station,
) -> None:
    r = api_client.get(f"/api/v{settings.API_VERSION}/stations/")
    names = [s["name"] for s in r.json()]
    assert names == sorted(names)


# ---------------------------------------------------------------------------
# GET /api/v1/departures/?from=&to=&date=
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_departures_search(
    api_client: APIClient,
    station_a: Station,
    station_d: Station,
    seat: Seat,
    seat2: Seat,
    departure: Departure,
) -> None:
    r = api_client.get(
        f"/api/v{settings.API_VERSION}/departures/?from={station_a.code}&to={station_d.code}&date={departure.date.isoformat()}"
    )
    assert r.status_code == 200, r.json()
    deps = r.json()
    assert len(deps) == 1
    assert deps[0]["uuid"] == str(departure.uuid)
    assert deps[0]["free_seat_count"] == 2


@pytest.mark.django_db
def test_departures_search_missing_params(api_client: APIClient) -> None:
    r = api_client.get(f"/api/v{settings.API_VERSION}/departures/")
    assert r.status_code == 400, r.json()


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_departures_search_no_results(
    api_client: APIClient,
    station_a: Station,
    station_d: Station,
    departure: Departure,
) -> None:
    r = api_client.get(
        f"/api/v{settings.API_VERSION}/departures/?from={station_a.code}&to={station_d.code}&date=2099-01-01"
    )
    assert r.status_code == 200, r.json()
    assert r.json() == []


@pytest.mark.django_db
def test_departures_search_invalid_station_codes(api_client: APIClient, station_a: Station) -> None:
    r = api_client.get(
        f"/api/v{settings.API_VERSION}/departures/?from=UNKNOWN&to={station_a.code}&date=2026-05-01"
    )
    assert r.status_code == 400, r.json()
    r = api_client.get(
        f"/api/v{settings.API_VERSION}/departures/?from={station_a.code}&to=UNKNOWN&date=2026-05-01"
    )
    assert r.status_code == 400, r.json()


@pytest.mark.django_db
def test_departures_search_from_to_same(api_client: APIClient, station_a: Station) -> None:
    r = api_client.get(
        f"/api/v{settings.API_VERSION}/departures/?from={station_a.code}&to={station_a.code}&date=2026-05-01"
    )
    assert r.status_code == 200, r.json()
    assert r.json() == []


@pytest.mark.django_db
def test_departures_search_invalid_date(
    api_client: APIClient, station_a: Station, station_b: Station
) -> None:
    r = api_client.get(
        f"/api/v{settings.API_VERSION}/departures/?from={station_a.code}&to={station_b.code}&date=invalid"
    )
    assert r.status_code == 400, r.json()


@pytest.mark.django_db
def test_departures_invalid_station_range(
    api_client: APIClient, departure: Departure, station_a: Station, station_b: Station
) -> None:
    """Station codes in the wrong order (to before from) return empty list."""
    r = api_client.get(
        f"/api/v{settings.API_VERSION}/departures/?from={station_b.code}&to={station_a.code}&date={departure.date.isoformat()}"
    )
    assert r.status_code == 200, r.json()
    assert r.json() == []


@pytest.mark.django_db
def test_departures_skip_non_matching_departures(
    api_client: APIClient,
    departure: Departure,
    backward_departure: Departure,
    station_a: Station,
    station_b: Station,
) -> None:
    """Departure that doesn't cover the requested station pair is not returned."""
    r = api_client.get(
        f"/api/v{settings.API_VERSION}/departures/?from={station_b.code}&to={station_a.code}&date={departure.date.isoformat()}"
    )
    assert r.status_code == 200, r.json()
    assert len(r.json()) == 1
    assert r.json()[0]["uuid"] == str(backward_departure.uuid)


# ---------------------------------------------------------------------------
# GET /api/v1/departures/{uuid}/seats/?from=&to=
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_seats_view(
    api_client: APIClient,
    station_a: Station,
    station_d: Station,
    seat: Seat,
    seat2: Seat,
    departure: Departure,
) -> None:
    r = api_client.get(
        f"/api/v{settings.API_VERSION}/departures/{departure.uuid}/seats/?from={station_a.code}&to={station_d.code}"
    )
    assert r.status_code == 200, r.json()
    cars = r.json()["cars"]
    assert len(cars) == 1
    assert len(cars[0]["seats"]) == 2
    # Check schema: each seat has expected keys
    for s in cars[0]["seats"]:
        assert set(s.keys()) >= {"number", "seat_type", "status", "price"}


@pytest.mark.django_db
def test_seats_view_no_results(
    api_client: APIClient,
    station_b: Station,
    station_c: Station,
    departure: Departure,
) -> None:
    r = api_client.get(
        f"/api/v{settings.API_VERSION}/departures/{departure.uuid}/seats/?from={station_b.code}&to={station_c.code}"
    )
    assert r.status_code == 200, r.json()
    assert r.json() == {"cars": []}


@pytest.mark.django_db
def test_seats_view_departure_not_found(
    api_client: APIClient,
    station_a: Station,
    station_d: Station,
) -> None:
    r = api_client.get(
        f"/api/v{settings.API_VERSION}/departures/{uuid4()}/seats/?from={station_a.code}&to={station_d.code}"
    )
    assert r.status_code == 404, r.json()


@pytest.mark.django_db
def test_seats_view_missing_params(api_client: APIClient, departure: Departure) -> None:
    r = api_client.get(f"/api/v{settings.API_VERSION}/departures/{departure.uuid}/seats/")
    assert r.status_code == 400, r.json()


@pytest.mark.django_db
def test_seats_view_invalid_station_codes(
    api_client: APIClient, departure: Departure, station_a: Station
) -> None:
    r = api_client.get(
        f"/api/v{settings.API_VERSION}/departures/{departure.uuid}/seats/?from=UNKNOWN&to={station_a.code}"
    )
    assert r.status_code == 400, r.json()
    r2 = api_client.get(
        f"/api/v{settings.API_VERSION}/departures/{departure.uuid}/seats/?from={station_a.code}&to=UNKNOWN"
    )
    assert r2.status_code == 400, r2.json()


# ---------------------------------------------------------------------------
# POST /api/v1/orders/
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_order_create(
    api_client: APIClient,
    station_a: Station,
    station_d: Station,
    car: Car,
    seat: Seat,
    departure: Departure,
    passenger: Passenger,
) -> None:
    r = api_client.post(
        f"/api/v{settings.API_VERSION}/orders/",
        create_order_payload(
            departure,
            station_a,
            station_d,
            items=[
                make_order_item(
                    car_number=car.number,
                    seat_number=seat.number,
                    passenger=passenger,
                ),
            ],
            expected_total_price=1000,
        ),
        format="json",
    )
    assert r.status_code == 201, r.json()
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
    station_a: Station,
    station_d: Station,
    car: Car,
    seat: Seat,
    departure: Departure,
    passenger: Passenger,
) -> None:
    payload = create_order_payload(
        departure,
        station_a,
        station_d,
        items=[
            make_order_item(
                car_number=car.number,
                seat_number=seat.number,
                passenger=passenger,
            ),
        ],
        expected_total_price=1000,
    )
    api_client.post(f"/api/v{settings.API_VERSION}/orders/", payload, format="json")
    r2 = api_client.post(f"/api/v{settings.API_VERSION}/orders/", payload, format="json")
    assert r2.status_code == 409, r2.json()


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_order_create_missing_field_400(api_client: APIClient) -> None:
    r = api_client.post(f"/api/v{settings.API_VERSION}/orders/", {}, format="json")
    assert r.status_code == 400, r.json()


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_order_create_empty_items_400(
    api_client: APIClient,
    station_a: Station,
    station_d: Station,
    departure: Departure,
) -> None:
    """Serializer rejects empty items list."""
    r = api_client.post(
        f"/api/v{settings.API_VERSION}/orders/",
        {
            "departure_uuid": str(departure.uuid),
            "station_from_code": station_a.code,
            "station_to_code": station_d.code,
            "items": [],
        },
        format="json",
    )
    assert r.status_code == 400, r.json()
    assert "items" in r.json()


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_order_create_same_station_400(
    api_client: APIClient,
    station_a: Station,
    station_d: Station,
    car: Car,
    seat: Seat,
    departure: Departure,
    passenger: Passenger,
) -> None:
    """Serializer rejects from == to."""
    payload = create_order_payload(
        departure,
        station_a,
        station_d,
        items=[
            make_order_item(
                car_number=car.number,
                seat_number=seat.number,
                passenger=passenger,
            ),
        ],
        expected_total_price=1000,
    )
    payload["station_to_code"] = payload["station_from_code"]
    r = api_client.post(f"/api/v{settings.API_VERSION}/orders/", payload, format="json")
    assert r.status_code == 400, r.json()


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_order_create_invalid_gender_400(
    api_client: APIClient,
    station_a: Station,
    station_d: Station,
    car: Car,
    seat: Seat,
    departure: Departure,
    passenger: Passenger,
) -> None:
    """Serializer rejects invalid gender choice."""
    payload = create_order_payload(
        departure,
        station_a,
        station_d,
        items=[
            make_order_item(
                car_number=car.number,
                seat_number=seat.number,
                passenger=passenger,
            ),
        ],
        expected_total_price=1000,
    )
    payload["items"][0]["passenger"]["gender"] = "invalid"
    r = api_client.post(f"/api/v{settings.API_VERSION}/orders/", payload, format="json")
    assert r.status_code == 400, r.json()


@pytest.mark.django_db
def test_order_create_invalid_station_id_400(
    api_client: APIClient,
    station_a: Station,
    station_d: Station,
    car: Car,
    seat: Seat,
    departure: Departure,
    passenger: Passenger,
) -> None:
    payload = create_order_payload(
        departure,
        station_a,
        station_d,
        items=[
            make_order_item(
                car_number=car.number,
                seat_number=seat.number,
                passenger=passenger,
            ),
        ],
        expected_total_price=1000,
    )
    payload["station_to_code"] = "UNKNOWN"
    r = api_client.post(f"/api/v{settings.API_VERSION}/orders/", payload, format="json")
    assert r.status_code == 400, r.json()


@pytest.mark.django_db
def test_order_create_invalid_departure_uuid_400(
    api_client: APIClient,
    station_a: Station,
    station_d: Station,
    car: Car,
    seat: Seat,
    departure: Departure,
    passenger: Passenger,
) -> None:
    payload = create_order_payload(
        departure,
        station_a,
        station_d,
        items=[
            make_order_item(
                car_number=car.number,
                seat_number=seat.number,
                passenger=passenger,
            ),
        ],
        expected_total_price=1000,
    )
    payload["departure_uuid"] = str(uuid4())
    r = api_client.post(f"/api/v{settings.API_VERSION}/orders/", payload, format="json")
    assert r.status_code == 400, r.json()


@pytest.mark.django_db
def test_order_create_invalid_station_range_400(
    api_client: APIClient,
    station_a: Station,
    station_d: Station,
    car: Car,
    seat: Seat,
    departure: Departure,
    passenger: Passenger,
) -> None:
    payload = create_order_payload(
        departure,
        station_d,
        station_a,
        items=[
            make_order_item(
                car_number=car.number,
                seat_number=seat.number,
                passenger=passenger,
            ),
        ],
        expected_total_price=1000,
    )
    r = api_client.post(f"/api/v{settings.API_VERSION}/orders/", payload, format="json")
    assert r.status_code == 400, r.json()


@pytest.mark.django_db
def test_order_create_invalid_seat_number_400(
    api_client: APIClient,
    station_a: Station,
    station_d: Station,
    car: Car,
    seat: Seat,
    departure: Departure,
    passenger: Passenger,
) -> None:
    payload = create_order_payload(
        departure,
        station_a,
        station_d,
        items=[
            make_order_item(
                car_number=car.number,
                seat_number=seat.number,
                passenger=passenger,
            ),
        ],
        expected_total_price=1000,
    )
    payload["items"][0]["seat_number"] = 99
    r = api_client.post(f"/api/v{settings.API_VERSION}/orders/", payload, format="json")
    assert r.status_code == 400, r.json()


@pytest.mark.django_db
def test_order_create_invalid_car_number_400(
    api_client: APIClient,
    station_a: Station,
    station_d: Station,
    car: Car,
    seat: Seat,
    departure: Departure,
    passenger: Passenger,
) -> None:
    payload = create_order_payload(
        departure,
        station_a,
        station_d,
        items=[
            make_order_item(
                car_number=car.number,
                seat_number=seat.number,
                passenger=passenger,
            ),
        ],
        expected_total_price=1000,
    )
    payload["items"][0]["car_number"] = 99
    r = api_client.post(f"/api/v{settings.API_VERSION}/orders/", payload, format="json")
    assert r.status_code == 400, r.json()


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_order_create_price_changed_409(
    api_client: APIClient,
    station_a: Station,
    station_d: Station,
    car: Car,
    seat: Seat,
    departure: Departure,
    passenger: Passenger,
) -> None:
    """When expected_total_price doesn't match the actual price, return 409 with actual price."""
    payload = create_order_payload(
        departure,
        station_a,
        station_d,
        items=[make_order_item(car.number, seat.number, passenger)],
        expected_total_price=999,  # actual is 1000
    )
    r = api_client.post(f"/api/v{settings.API_VERSION}/orders/", payload, format="json")
    assert r.status_code == 409, r.json()
    data = r.json()
    assert "actual_total_price" in data
    assert Decimal(data["actual_total_price"]) == Decimal("1000.00")


# ---------------------------------------------------------------------------
# GET /api/v1/orders/{uuid}/
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_order_retrieve(
    api_client: APIClient,
    station_a: Station,
    station_d: Station,
    car: Car,
    seat: Seat,
    departure: Departure,
    passenger: Passenger,
) -> None:
    r = api_client.post(
        f"/api/v{settings.API_VERSION}/orders/",
        create_order_payload(
            departure,
            station_a,
            station_d,
            items=[
                make_order_item(
                    car_number=car.number,
                    seat_number=seat.number,
                    passenger=passenger,
                ),
            ],
            expected_total_price=1000,
        ),
        format="json",
    )
    order_uuid = r.json()["uuid"]
    r2 = api_client.get(f"/api/v{settings.API_VERSION}/orders/{order_uuid}/")
    assert r2.status_code == 200, r2.json()
    assert r2.json()["uuid"] == order_uuid


@pytest.mark.django_db
def test_order_retrieve_not_found(api_client: APIClient) -> None:
    r = api_client.get(f"/api/v{settings.API_VERSION}/orders/{uuid4()}/")
    assert r.status_code == 404, r.json()
