from rest_framework import serializers

from borrowings.notifications import send_telegram_notification
from payments.models import Payment
from payments.utils import get_payment_info


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = (
            "id",
            "status",
            "type",
            "borrowing",
            "session_url",
            "session_id",
            "money_to_pay",
        )

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        message = "Payment has been made successfully\n" + get_payment_info(instance)
        send_telegram_notification(message)
        return instance


class PaymentDetailSerializer(PaymentSerializer):
    borrowing = serializers.StringRelatedField(many=False, read_only=True)
