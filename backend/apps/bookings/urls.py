from django.urls import path

from apps.bookings.views import OrderCreateView, OrderDetailView

urlpatterns = [
    path("", OrderCreateView.as_view(), name="order-create"),
    path("<uuid:uuid>/", OrderDetailView.as_view(), name="order-detail"),
]
