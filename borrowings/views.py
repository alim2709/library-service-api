from datetime import datetime

from django.db import transaction
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet
from rest_framework.response import Response

from borrowings.models import Borrowing
from borrowings.serializers import BorrowingSerializer, BorrowingDetailSerializer


class BorrowingViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet,
):
    queryset = Borrowing.objects.all()
    serializer_class = BorrowingSerializer

    def get_serializer_class(self):
        if self.action == "retrieve":
            return BorrowingDetailSerializer
        return BorrowingSerializer

    @staticmethod
    def _params_to_ints(qs):
        """Converts a list of string IDs to a list of integers"""
        return [int(str_id) for str_id in qs.split(",")]

    def get_queryset(self):
        queryset = self.queryset
        if self.action in ("list", "retrieve"):
            queryset = queryset.filter(user=self.request.user)

        """Filtering by user and is active borrowing"""
        user = self.request.query_params.get("user")
        is_active = self.request.query_params.get("is_active")
        if user:
            user_id = self._params_to_ints(user)
            queryset = queryset.filter(user_id__in=user_id)
        if is_active:
            queryset = queryset.filter(actual_return_date__isnull=True)

        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @transaction.atomic
    @action(methods=["POST"], detail=True, url_path="borrowing_return")
    def borrowing_return(self, request, pk=None):
        borrowing = self.get_object()
        user = self.request.user
        borrowing.actual_return_date = datetime.now()
        borrowing.book.inventory += 1
        borrowing.book.save()
        borrowing.save()
        return Response({"status": "borrowing returned"})
