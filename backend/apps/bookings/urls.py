from django.urls import path

from apps.bookings.views import OrderCreateView, OrderDetailView

urlpatterns = [
    path("orders/", OrderCreateView.as_view(), name="order-create"),
    path("orders/<uuid:uuid>/", OrderDetailView.as_view(), name="order-detail"),
]
