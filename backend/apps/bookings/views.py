from rest_framework import status
from rest_framework.generics import RetrieveAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bookings.exceptions import DepartureNotFoundError, SeatNotFoundError, SeatUnavailableError
from apps.bookings.models import Order
from apps.bookings.serializers import CreateOrderSerializer, OrderSerializer
from apps.bookings.services import create_order
from apps.routes.exceptions import InvalidStationRangeError
from apps.stations.exceptions import InvalidStationCodeError


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
            )
        except SeatUnavailableError as e:
            return Response(
                {
                    "detail": str(e),
                    "car_number": e.car_number,
                    "seat_number": e.seat_number,
                },
                status=status.HTTP_409_CONFLICT,
            )
        except (
            DepartureNotFoundError,
            InvalidStationCodeError,
            InvalidStationRangeError,
            SeatNotFoundError,
        ) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # create_order populates order._prefetched_objects_cache with bookings
        # and all their FK relations — no extra query needed.
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
