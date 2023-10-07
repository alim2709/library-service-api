import stripe
from rest_framework.decorators import api_view, action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import mixins, status
from rest_framework.viewsets import GenericViewSet

from payments.models import Payment
from payments.serializers import PaymentSerializer, PaymentDetailSerializer


class PaymentViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PaymentDetailSerializer
        return PaymentSerializer

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
            return Response(serializer.data, status=status.HTTP_200_OK)

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
