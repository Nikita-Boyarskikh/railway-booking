import pytest

from apps.bookings.services import SeatUnavailableError, create_order


def _item(seat_id):
    return {
        "seat_id": seat_id,
        "passenger_name": "John",
        "passenger_passport": "123",
        "passenger_gender": "male",
        "passenger_birth_date": "1990-01-01",
    }


@pytest.mark.django_db
def test_non_overlapping_segments_share_seat(demo_data):
    d = demo_data
    s = d["stations"]
    # Book A→B on seat 1
    create_order(d["departure"].id, s[0].id, s[1].id, [_item(d["seat"].id)])
    # Book C→D on same seat — should succeed (non-overlapping)
    order2 = create_order(d["departure"].id, s[2].id, s[3].id, [_item(d["seat"].id)])
    assert order2.bookings.count() == 1


@pytest.mark.django_db
def test_overlapping_segments_conflict(demo_data):
    d = demo_data
    s = d["stations"]
    # Book A→C on seat 1
    create_order(d["departure"].id, s[0].id, s[2].id, [_item(d["seat"].id)])
    # Try B→D on same seat — overlaps at B→C
    with pytest.raises(SeatUnavailableError):
        create_order(d["departure"].id, s[1].id, s[3].id, [_item(d["seat"].id)])
