from datetime import datetime

import rest_framework_simplejwt.authentication
from django.db import transaction
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import mixins, status
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
    queryset = Borrowing.objects.all().select_related("book", "user")
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

    def get_serializer_context(self) -> dict:
        context = super().get_serializer_context()

        if self.action == "borrowing_return":
            context["request"] = self.request

        return context

    @staticmethod
    def _params_to_ints(qs):
        """Converts a list of string IDs to a list of integers"""
        return [int(str_id) for str_id in qs.split(",")]

    @staticmethod
    def _params_to_bool(qs: str) -> bool:
        """Converts a str to bool True or False"""
        return qs.lower() == "true"

    def get_queryset(self):
        queryset = self.queryset
        if self.action in ("list", "retrieve") and not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)

        """Filtering by user and is active borrowing"""
        user = self.request.query_params.get("user")
        is_active = self.request.query_params.get("is_active")
        if self.request.user.is_staff:
            """Filtering for admin users"""
            if user:
                user_id = self._params_to_ints(user)
                queryset = queryset.filter(user_id__in=user_id)
            if is_active and self._params_to_bool(is_active):
                queryset = queryset.filter(actual_return_date__isnull=True)
            if is_active and not self._params_to_bool(is_active):
                queryset = queryset.filter(actual_return_date__isnull=False)
        if not self.request.user.is_staff and is_active:
            """Filtering for non-admin users"""
            if self._params_to_bool(is_active):
                queryset = queryset.filter(
                    actual_return_date__isnull=True, user=self.request.user
                )
            else:
                queryset = queryset.filter(
                    actual_return_date__isnull=False, user=self.request.user
                )
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @transaction.atomic
    @action(
        methods=["POST"],
        detail=True,
        url_path="return",
        serializer_class=BorrowingReturnSerializer,
    )
    def borrowing_return(self, request, pk=None):
        """Endpoint for returning borrowing book"""
        borrowing = self.get_object()
        book = borrowing.book
        actual_return_date = datetime.now().date()

        serializer_update = BorrowingReturnSerializer(
            borrowing,
            context={"request": self.request},
            data={"actual_return_date": actual_return_date},
            partial=True,
        )
        serializer_update.is_valid(raise_exception=True)
        serializer_update.save()
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

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "user",
                type={"type": "list", "items": {"type": "number"}},
                description="Filter by users  (ex. ?user=1,2)",
            ),
            OpenApiParameter(
                "destination",
                type={"type": "string"},
                description="Filter by is_active borrowing  (ex. ?is_active=True)",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
