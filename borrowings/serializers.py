from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from borrowings.models import Borrowing
from payments.models import Payment
from payments.stripe_session import create_stripe_session_and_payment


class BorrowingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrowing
        fields = (
            "id",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
            "book",
            "user",
        )


class BorrowingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrowing
        fields = ("id", "borrow_date", "expected_return_date", "book")

    def validate(self, attrs):
        data = super(BorrowingCreateSerializer, self).validate(attrs)
        book = attrs["book"]
        user = self.context["request"].user
        pending_payments = Payment.objects.filter(borrowing__user=user).filter(
            status="Pending"
        )
        if pending_payments:
            raise ValidationError(
                detail="You have one or more pending payments. You can't make borrowings until you pay for them."
            )
        if book.inventory == 0:
            raise serializers.ValidationError(
                {"book_inventory": f"{book.title} out of stock at this moment"}
            )
        return data

    @transaction.atomic()
    def create(self, validated_data):
        borrowing = Borrowing.objects.create(**validated_data)
        book = validated_data["book"]
        book.inventory -= 1
        book.save()

        create_stripe_session_and_payment(
            borrowing, request=self.context["request"], payment_type="Payment"
        )
        return borrowing


class BorrowingDetailSerializer(BorrowingCreateSerializer):
    user = serializers.StringRelatedField(many=False, read_only=True)
    book = serializers.StringRelatedField(many=False, read_only=True)
    payments = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = Borrowing
        fields = (
            "id",
            "expected_return_date",
            "actual_return_date",
            "book",
            "user",
            "payments",
        )
        read_only_fields = ("id", "payments")


class BorrowingReturnSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrowing
        fields = (
            "id",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
        )
        read_only_fields = ("id", "borrow_date", "expected_return_date")

    def validate(self, attrs) -> dict:
        if self.instance.actual_return_date is not None:
            raise ValidationError(detail="Borrowing has been already returned.")
        return super().validate(attrs=attrs)
