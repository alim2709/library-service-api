from datetime import datetime
from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from borrowings.models import Borrowing
from borrowings.notifications import send_telegram_notification
from borrowings.utils import get_borrowing_info
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
        user = self.context["request"].user
        pending_payments = Payment.objects.filter(borrowing__user=user).filter(
            status="Pending"
        )
        if pending_payments:
            raise ValidationError(
                detail="You have one or more pending payments. You can't make borrowings until you pay for them."
            )
        return data

    def validate_expected_return_date(self, value):
        if value < datetime.now().date():
            raise ValidationError(
                detail="You can't put expected return date in the past!!!"
            )
        return value

    def validate_book(self, value):
        if value.inventory == 0:
            raise serializers.ValidationError(
                {"book_inventory": f"{value.title} out of stock at this moment"}
            )
        return value

    @transaction.atomic()
    def create(self, validated_data):
        borrowing = Borrowing.objects.create(**validated_data)
        book = validated_data["book"]
        book.inventory -= 1
        book.save()

        create_stripe_session_and_payment(
            borrowing, request=self.context["request"], payment_type="Payment"
        )
        message = "New borrowing created:\n" + get_borrowing_info(borrowing)
        send_telegram_notification(message)

        return borrowing


class BorrowingDetailSerializer(BorrowingCreateSerializer):
    user = serializers.SlugRelatedField(many=False, read_only=True, slug_field="email")
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

    @transaction.atomic
    def validate(self, attrs):
        borrowing = self.instance
        if borrowing.actual_return_date is not None:
            raise ValidationError(detail="Borrowing has been already returned.")

        actual_return_date = datetime.now().date()
        expected_return_date = borrowing.expected_return_date
        if actual_return_date > expected_return_date:
            overdue_period = (actual_return_date - expected_return_date).days
            session = create_stripe_session_and_payment(
                borrowing,
                self.context["request"],
                payment_type="Fine",
                overdue_days=overdue_period,
            )
            raise ValidationError(
                {
                    "message": "Your return is overdue please provide Fine payment",
                    "payment_url": session.url,
                }
            )

        return super().validate(attrs=attrs)

    @transaction.atomic
    def update(self, instance, validated_data):
        book = instance.book
        instance.actual_return_date = datetime.now().date()
        instance.save()
        book.inventory += 1
        book.save()
        return instance
