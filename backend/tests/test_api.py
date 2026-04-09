import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_full_flow(demo_data):
    d = demo_data
    s = d["stations"]
    client = APIClient()

    # list stations
    r = client.get("/api/stations/")
    assert r.status_code == 200
    assert len(r.json()) == 4

    # search departures
    r = client.get(f"/api/departures/?from={s[0].id}&to={s[3].id}&date=2026-05-01")
    assert r.status_code == 200
    deps = r.json()
    assert len(deps) == 1
    assert deps[0]["free_seat_count"] == 2

    # seats
    r = client.get(f"/api/departures/{d['departure'].id}/seats/?from={s[0].id}&to={s[3].id}")
    assert r.status_code == 200
    cars = r.json()["cars"]
    assert len(cars) == 1

    # create order
    payload = {
        "departure_id": d["departure"].id,
        "station_from_id": s[0].id,
        "station_to_id": s[3].id,
        "items": [
            {
                "seat_id": d["seat"].id,
                "passenger_name": "Jane",
                "passenger_passport": "X1",
                "passenger_gender": "female",
                "passenger_birth_date": "1985-06-01",
            }
        ],
    }
    r = client.post("/api/orders/", payload, format="json")
    assert r.status_code == 201, r.content

    # conflict on duplicate booking
    r2 = client.post("/api/orders/", payload, format="json")
    assert r2.status_code == 409
