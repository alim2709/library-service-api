from django.db import transaction
from rest_framework import serializers

from borrowings.models import Borrowing


class BorrowingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrowing
        fields = (
            "id",
            "borrow_date",
            "expected_return_date",
            "book",
        )

    @transaction.atomic()
    def create(self, validated_data):
        book = validated_data["book"]
        book.inventory -= 1
        book.save()
        return Borrowing.objects.create(**validated_data)


class BorrowingDetailSerializer(BorrowingSerializer):
    user = serializers.StringRelatedField(many=False, read_only=True)
    book = serializers.StringRelatedField(many=False, read_only=True)

    class Meta:
        model = Borrowing
        fields = ("id", "expected_return_date", "actual_return_date", "book", "user")
