import pytest


@pytest.fixture
def demo_data(db):
    from datetime import date, time, timedelta
    from decimal import Decimal

    from constance import config

    from apps.routes.models import Route, RouteSegment
    from apps.stations.models import Segment, Station
    from apps.trains.models import Car, Departure, Seat, Train

    config.BASE_PRICE = Decimal("100")

    s1 = Station.objects.create(name="A", code="A")
    s2 = Station.objects.create(name="B", code="B")
    s3 = Station.objects.create(name="C", code="C")
    s4 = Station.objects.create(name="D", code="D")

    seg1 = Segment.objects.create(station_from=s1, station_to=s2, distance_km=100, base_price=200)
    seg2 = Segment.objects.create(station_from=s2, station_to=s3, distance_km=100, base_price=300)
    seg3 = Segment.objects.create(station_from=s3, station_to=s4, distance_km=100, base_price=400)

    route = Route.objects.create(name="A-D", price_factor=Decimal("1.0"))
    RouteSegment.objects.create(route=route, segment=seg1, order=0, stop_duration=timedelta(0))
    RouteSegment.objects.create(route=route, segment=seg2, order=1, stop_duration=timedelta(0))
    RouteSegment.objects.create(route=route, segment=seg3, order=2, stop_duration=timedelta(0))

    train = Train.objects.create(
        route=route,
        number="100",
        name="T",
        avg_speed_kmh=Decimal("100"),
        price_factor=Decimal("1.0"),
    )
    car = Car.objects.create(train=train, number=1, price_factor=Decimal("1.0"))
    seat = Seat.objects.create(car=car, number=1, price_factor=Decimal("1.0"))
    seat2 = Seat.objects.create(car=car, number=2, price_factor=Decimal("1.0"))

    departure = Departure.objects.create(
        train=train, date=date(2026, 5, 1), departure_time=time(10, 0)
    )

    return {
        "stations": [s1, s2, s3, s4],
        "route": route,
        "train": train,
        "car": car,
        "seat": seat,
        "seat2": seat2,
        "departure": departure,
    }
