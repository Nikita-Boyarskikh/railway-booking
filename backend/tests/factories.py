"""factory_boy factories for railway-booking models.

Use these when a test needs objects with **non-default attribute values**
(e.g. custom ``price_factor``, ``avg_speed_kmh``).  For the standard
A→B→C→D topology shared by the majority of tests, the pytest fixtures
in ``conftest.py`` remain the better choice.
"""

import factory
from djmoney.money import Money
from factory.django import DjangoModelFactory
from faker import Faker

from apps.bookings.models import Booking, Order, Passenger
from apps.routes.models import Route, RouteSegment
from apps.stations.models import Connection, Station
from apps.trains.models import Car, CarType, Departure, Seat, SeatType, Train

fake = Faker()


class StationFactory(DjangoModelFactory):  # type: ignore[type-arg]
    class Meta:
        model = Station

    name = factory.Sequence(lambda n: f"Station {n}")
    code = factory.Sequence(lambda n: f"S{n:03d}")


class ConnectionFactory(DjangoModelFactory):  # type: ignore[type-arg]
    class Meta:
        model = Connection

    station_from = factory.SubFactory(StationFactory)
    station_to = factory.SubFactory(StationFactory)
    distance_km = factory.Faker("random_number")

    @factory.lazy_attribute
    def base_price(self) -> Money:
        return Money(fake.pydecimal(left_digits=8, right_digits=2), "USD")


class RouteFactory(DjangoModelFactory):  # type: ignore[type-arg]
    class Meta:
        model = Route

    name = factory.Sequence(lambda n: f"Route {n}")
    price_factor = factory.Faker("pydecimal", positive=True, left_digits=3, right_digits=3)


class RouteSegmentFactory(DjangoModelFactory):  # type: ignore[type-arg]
    class Meta:
        model = RouteSegment

    route = factory.SubFactory(RouteFactory)
    connection = factory.SubFactory(ConnectionFactory)
    order = factory.Sequence(lambda n: n)
    stop_duration = factory.Faker("time_delta")


class TrainFactory(DjangoModelFactory):  # type: ignore[type-arg]
    class Meta:
        model = Train

    route = factory.SubFactory(RouteFactory)
    number = factory.Sequence(lambda n: f"T{n:04d}")
    name = factory.Sequence(lambda n: f"Train {n}")
    avg_speed_kmh = factory.Faker("pyfloat", positive=True)
    price_factor = factory.Faker("pydecimal", positive=True, left_digits=3, right_digits=3)


class CarFactory(DjangoModelFactory):  # type: ignore[type-arg]
    class Meta:
        model = Car

    train = factory.SubFactory(TrainFactory)
    number = factory.Sequence(lambda n: n + 1)
    car_type = factory.Faker("enum", enum_cls=CarType)
    price_factor = factory.Faker("pydecimal", positive=True, left_digits=3, right_digits=3)


class SeatFactory(DjangoModelFactory):  # type: ignore[type-arg]
    class Meta:
        model = Seat

    car = factory.SubFactory(CarFactory)
    number = factory.Sequence(lambda n: n + 1)
    seat_type = factory.Faker("enum", enum_cls=SeatType)
    price_factor = factory.Faker("pydecimal", positive=True, left_digits=3, right_digits=3)


class DepartureFactory(DjangoModelFactory):  # type: ignore[type-arg]
    class Meta:
        model = Departure

    train = factory.SubFactory(TrainFactory)
    date = factory.Faker("future_date")
    departure_time = factory.Faker("time_object")


class PassengerFactory(DjangoModelFactory):  # type: ignore[type-arg]
    class Meta:
        model = Passenger

    gender = factory.Faker("random_element", elements=["male", "female"])
    passport_number = factory.Faker("passport_number")
    birth_date = factory.Faker("date_of_birth")

    @factory.lazy_attribute
    def name(self) -> str:
        return fake.name_female() if self.gender == "female" else fake.name_male()


class OrderFactory(DjangoModelFactory):  # type: ignore[type-arg]
    class Meta:
        model = Order


class BookingFactory(DjangoModelFactory):  # type: ignore[type-arg]
    class Meta:
        model = Booking

    order = factory.SubFactory(OrderFactory)
    departure = factory.SubFactory(DepartureFactory)
    seat = factory.SubFactory(SeatFactory)
    station_from = factory.SubFactory(StationFactory)
    station_to = factory.SubFactory(StationFactory)
    passenger = factory.SubFactory(PassengerFactory)
