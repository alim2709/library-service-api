from django.urls import path

from payments.views import (
    PaymentViewSet,
)

urlpatterns = [
    path(
        "",
        PaymentViewSet.as_view(actions={"get": "list"}),
        name="payment-list",
    ),
    path(
        "<int:pk>/",
        PaymentViewSet.as_view(actions={"get": "retrieve"}),
        name="payment-detail",
    ),
    path(
        "success/",
        PaymentViewSet.as_view(actions={"get": "payment_success"}),
        name="payment-success",
    ),
    path(
        "cansel/",
        PaymentViewSet.as_view(actions={"get": "payment_cancel"}),
        name="payment-cancel",
    ),
]

app_name = "payments"
