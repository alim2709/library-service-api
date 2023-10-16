import stripe
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import mixins, status
from rest_framework.viewsets import GenericViewSet

from borrowings.notifications import send_telegram_notification
from payments.models import Payment
from payments.serializers import PaymentSerializer, PaymentDetailSerializer
from payments.utils import get_payment_info


class PaymentViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    authentication_classes = (
        rest_framework_simplejwt.authentication.JWTAuthentication,
    )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PaymentDetailSerializer
        return PaymentSerializer

    def get_queryset(self):
        queryset = self.queryset
        user = self.request.user
        if not user.is_staff:
            queryset = queryset.filter(borrowing__user=user)
        return queryset

    @action(methods=["GET"], detail=False, url_path="payment_success")
    def payment_success(self, request: Request):
        """Endpoint for successful stripe payment session"""
        session_id = request.query_params.get("session_id")
        payment = Payment.objects.get(session_id=session_id)
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == "paid":
            serializer = PaymentSerializer(
                payment, data={"status": "Paid"}, partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            message = "Payment has been made successfully\n" + get_payment_info(payment)
            send_telegram_notification(message)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["GET"], detail=False, url_path="payment_cancel")
    def payment_cancel(self, request: Request):
        """Endpoint for canceled stripe payment session"""
        session_id = request.query_params.get("session_id")
        payment = Payment.objects.get(session_id=session_id)
        serializer = PaymentSerializer(payment)
        data = {
            "message": "You can make a payment during the next 24 hours.",
            **serializer.data,
        }
        return Response(data=data, status=status.HTTP_200_OK)
