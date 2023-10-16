from datetime import datetime

import rest_framework_simplejwt.authentication
from django.db import transaction
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet
from rest_framework.response import Response

from borrowings.models import Borrowing
from borrowings.serializers import (
    BorrowingCreateSerializer,
    BorrowingDetailSerializer,
    BorrowingReturnSerializer,
    BorrowingSerializer,
)
from payments.models import Payment
from payments.stripe_session import create_stripe_session_and_payment


class BorrowingViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet,
):
    queryset = Borrowing.objects.all()
    serializer_class = BorrowingSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (
        rest_framework_simplejwt.authentication.JWTAuthentication,
    )

    def get_serializer_class(self):
        if self.action == "create":
            return BorrowingCreateSerializer
        if self.action == "retrieve":
            return BorrowingDetailSerializer
        return BorrowingSerializer

    @staticmethod
    def _params_to_ints(qs):
        """Converts a list of string IDs to a list of integers"""
        return [int(str_id) for str_id in qs.split(",")]

    def get_queryset(self):
        queryset = self.queryset
        if self.action in ("list", "retrieve") and not self.request.user.is_superuser:
            queryset = queryset.filter(user=self.request.user)

        """Filtering by user and is active borrowing"""
        user = self.request.query_params.get("user")
        is_active = self.request.query_params.get("is_active")
        if user:
            user_id = self._params_to_ints(user)
            queryset = queryset.filter(user_id__in=user_id)
        if is_active and is_active == "True":
            queryset = queryset.filter(actual_return_date__isnull=True)
        if is_active and is_active == "False":
            queryset = queryset.filter(actual_return_date__isnull=False)

        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @transaction.atomic
    @action(
        methods=["POST"],
        detail=True,
        url_path="borrowing_return",
        serializer_class=BorrowingReturnSerializer,
    )
    def borrowing_return(self, request, pk=None):
        borrowing = self.get_object()
        book = borrowing.book
        actual_return_date = datetime.now().date()
        expected_return_date = borrowing.expected_return_date

        serializer_update = BorrowingReturnSerializer(
            borrowing,
            data={"actual_return_date": actual_return_date},
            partial=True,
        )
        serializer_update.is_valid(raise_exception=True)
        serializer_update.save()
        book.inventory += 1
        book.save()
        if actual_return_date > expected_return_date:
            overdue_period = (actual_return_date - borrowing.expected_return_date).days
            session = create_stripe_session_and_payment(
                borrowing,
                self.request,
                payment_type="Fine",
                overdue_days=overdue_period,
            )
            info = {
                "message": "Your return is overdue please provide Fine payment",
                "payment_url": session.url,
            }
            return Response(info)
        return Response({"status": "borrowing returned"})

    @transaction.atomic
    @action(
        methods=["POST"],
        detail=True,
        url_path="update_session_url",
    )
    def update_expired_borrowing_session_url_and_sesion_id(self, request, pk=None):
        """Endpoint for updating session url & session id in borrowing payment info"""
        borrowing = self.get_object()
        payment = Payment.objects.get(borrowing=borrowing, type="Payment")
        if payment.status == "Expired":
            new_session_for_borrowing = create_stripe_session_and_payment(
                borrowing=borrowing, request=self.request, payment_type="Payment"
            )
            payment.status = "Pending"
            payment.session_id = new_session_for_borrowing.id
            payment.session_url = new_session_for_borrowing.url
            payment.save()
            return Response({"status": "Session url has been updated"})

        return Response({"status": "Session url is still active"})
