from rest_framework import status
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Order
from .serializers import OrderSerializer
from .services import InvalidRequestError, SeatUnavailableError, create_order


class OrderCreateView(APIView):
    def post(self, request):
        data = request.data
        try:
            order = create_order(
                departure_id=int(data["departure_id"]),
                station_from_id=int(data["station_from_id"]),
                station_to_id=int(data["station_to_id"]),
                items=data["items"],
            )
        except SeatUnavailableError as e:
            return Response(
                {"detail": str(e), "seat_id": e.seat_id},
                status=status.HTTP_409_CONFLICT,
            )
        except (InvalidRequestError, KeyError, ValueError, TypeError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class OrderDetailView(RetrieveAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
