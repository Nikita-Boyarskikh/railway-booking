import pytest

from apps.bookings.services import SeatUnavailableError, create_order


def _item(car_number, seat_number):
    return {
        "car_number": car_number,
        "seat_number": seat_number,
        "passenger_name": "John",
        "passenger_passport": "123",
        "passenger_gender": "male",
        "passenger_birth_date": "1990-01-01",
    }


@pytest.mark.django_db
def test_non_overlapping_segments_share_seat(demo_data):
    d = demo_data
    s = d["stations"]
    item = _item(d["car"].number, d["seat"].number)
    # Book A→B on seat 1
    create_order(d["departure"].uuid, s[0].code, s[1].code, [item])
    # Book C→D on same seat — should succeed (non-overlapping)
    order2 = create_order(d["departure"].uuid, s[2].code, s[3].code, [item])
    assert order2.bookings.count() == 1


@pytest.mark.django_db
def test_overlapping_segments_conflict(demo_data):
    d = demo_data
    s = d["stations"]
    item = _item(d["car"].number, d["seat"].number)
    # Book A→C on seat 1
    create_order(d["departure"].uuid, s[0].code, s[2].code, [item])
    # Try B→D on same seat — overlaps at B→C
    with pytest.raises(SeatUnavailableError):
        create_order(d["departure"].uuid, s[1].code, s[3].code, [item])
