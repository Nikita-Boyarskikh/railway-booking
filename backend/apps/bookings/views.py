from typing import TYPE_CHECKING

from django.conf import settings
from djmoney.money import Money
from rest_framework import status
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bookings.exceptions import (
    DepartureNotFoundError,
    PriceChangedError,
    SeatNotFoundError,
    SeatUnavailableError,
)
from apps.bookings.models import Order
from apps.bookings.serializers import CreateOrderSerializer, OrderSerializer
from apps.bookings.services import create_order
from apps.routes.exceptions import InvalidStationRangeError
from apps.stations.exceptions import InvalidStationCodeError

if TYPE_CHECKING:
    from rest_framework.request import Request


class OrderCreateView(APIView):
    """``POST /api/v1/orders/`` — create an order with one or more bookings."""

    def post(self, request: Request) -> Response:
        """Create an order. Returns 201 on success, 409 on seat conflict, 400 on bad input."""
        serializer = CreateOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            order = create_order(
                departure_uuid=data["departure_uuid"],
                station_from_code=data["station_from_code"],
                station_to_code=data["station_to_code"],
                items=data["items"],
                expected_total_price=Money(data["expected_total_price"], settings.DEFAULT_CURRENCY),
            )
        except PriceChangedError as e:
            return Response(
                {"detail": str(e), "actual_total_price": e.actual_total},
                status=status.HTTP_409_CONFLICT,
            )
        except SeatUnavailableError as e:
            return Response({"detail": str(e)}, status=status.HTTP_409_CONFLICT)
        except (
            DepartureNotFoundError,
            InvalidStationCodeError,
            InvalidStationRangeError,
            SeatNotFoundError,
        ) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class OrderDetailView(RetrieveAPIView[Order]):
    """``GET /api/v1/orders/{uuid}/`` — retrieve a single order by uuid."""

    queryset = Order.objects.prefetch_related(
        "bookings__departure",
        "bookings__seat__car",
        "bookings__station_from",
        "bookings__station_to",
        "bookings__passenger",
    )
    serializer_class = OrderSerializer
    lookup_field = "uuid"
    lookup_url_kwarg = "uuid"
