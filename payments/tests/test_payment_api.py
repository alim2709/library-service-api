import decimal
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from books.tests.test_book_api import sample_book
from borrowings.models import Borrowing
from payments.models import Payment
from payments.serializers import PaymentSerializer, PaymentDetailSerializer

SUCCESS_URL = reverse("payments:payment-success")
CANCEL_URL = reverse("payments:payment-cancel")
PAYMENT_URL = reverse("payments:payment-list")
BORROWING_DAYS = 7


def detail_url(payment_id):
    return reverse("payments:payment-detail", args=[payment_id])


class UnauthenticatedPaymentApiTests(APITestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(PAYMENT_URL)
        self.assertEquals(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedPaymentApiTests(APITestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "testunique@tests.com", "unique_password"
        )
        self.user2 = get_user_model().objects.create_user(
            "testunique1@tests.com", "unique_password"
        )
        self.client.force_authenticate(self.user)
        self.book = sample_book()
        self.borrowing = Borrowing.objects.create(
            expected_return_date=datetime.now().date() + timedelta(days=BORROWING_DAYS),
            book=self.book,
            user=self.user,
        )
        self.borrowing2 = Borrowing.objects.create(
            expected_return_date=datetime.now().date() + timedelta(days=BORROWING_DAYS),
            book=self.book,
            user=self.user2,
        )
        self.money_to_pay = decimal.Decimal(self.book.daily_fee * BORROWING_DAYS)
        self.payment_user = Payment.objects.create(
            status="Pending",
            type="Payment",
            borrowing=self.borrowing,
            session_url="https://checkout.stripe.com/c/pay/cs_test",
            session_id="cs_test",
            money_to_pay=self.money_to_pay,
        )
        self.payment_another_user = Payment.objects.create(
            status="PENDING",
            type="PAYMENT",
            borrowing=self.borrowing2,
            session_url="https://checkout.stripe.com/c/pay/cs_test1",
            session_id="cs_test1",
            money_to_pay=self.money_to_pay,
        )

    def test_list_payments(self):
        response = self.client.get(PAYMENT_URL)

        payments_only_auth_user = Payment.objects.filter(borrowing__user=self.user)
        serializer = PaymentSerializer(payments_only_auth_user, many=True)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data["results"], serializer.data)

    def test_retrieve_own_payment_detail(self):
        own_payment = self.payment_user
        another_user_payment = self.payment_another_user

        own_url_payment = detail_url(own_payment.id)
        another_user_url_payment = detail_url(another_user_payment.id)

        response_own = self.client.get(own_url_payment)
        response_another_user = self.client.get(another_user_url_payment)

        serializer_own = PaymentDetailSerializer(own_payment)

        self.assertEquals(response_own.status_code, status.HTTP_200_OK)
        self.assertEquals(response_own.data, serializer_own.data)
        self.assertEquals(response_another_user.status_code, status.HTTP_404_NOT_FOUND)

    @patch("payments.views.send_telegram_notification")
    @patch("payments.views.stripe.checkout.Session.retrieve")
    def test_payment_success(
        self,
        mock_data,
        mock_data1,
    ):
        mock_data.return_value = MagicMock(payment_status="paid")
        url_success_payment = (
            SUCCESS_URL + f"?session_id={self.payment_user.session_id}"
        )

        response = self.client.get(url_success_payment)

        payment = Payment.objects.get(session_id=self.payment_user.session_id)
        serializer = PaymentSerializer(payment)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data, serializer.data)

    def test_payment_cancel(self):
        url_cancel_payment = CANCEL_URL + f"?session_id={self.payment_user.session_id}"

        response = self.client.get(url_cancel_payment)
        serializer = PaymentSerializer(self.payment_user)

        self.assertEquals(
            response.data["message"], "You can make a payment during the next 24 hours."
        )
        self.assertEquals(response.data["id"], serializer.data["id"])
        self.assertEquals(response.data["status"], serializer.data["status"])
        self.assertEquals(response.data["type"], serializer.data["type"])
        self.assertEquals(response.data["borrowing"], serializer.data["borrowing"])
        self.assertEquals(response.data["session_url"], serializer.data["session_url"])
        self.assertEquals(response.data["session_id"], serializer.data["session_id"])
        self.assertEquals(
            response.data["money_to_pay"], serializer.data["money_to_pay"]
        )


class AdminPaymentApiTests(APITestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@admin.com", "testpass1", is_staff=True
        )
        self.user2 = get_user_model().objects.create_user(
            "testunique1@tests.com", "unique_password"
        )
        self.user3 = get_user_model().objects.create_user(
            "testunique3@tests.com", "unique_password"
        )
        self.book = sample_book()
        self.client.force_authenticate(self.user)
        self.borrowing1 = Borrowing.objects.create(
            expected_return_date=datetime.now().date() + timedelta(days=BORROWING_DAYS),
            book=self.book,
            user=self.user2,
        )
        self.borrowing2 = Borrowing.objects.create(
            expected_return_date=datetime.now().date() + timedelta(days=BORROWING_DAYS),
            book=self.book,
            user=self.user3,
        )
        self.money_to_pay = decimal.Decimal(self.book.daily_fee * BORROWING_DAYS)
        self.payment_user = Payment.objects.create(
            status="Pending",
            type="Payment",
            borrowing=self.borrowing1,
            session_url="https://checkout.stripe.com/c/pay/cs_test",
            session_id="cs_test",
            money_to_pay=self.money_to_pay,
        )
        self.payment_another_user = Payment.objects.create(
            status="PENDING",
            type="PAYMENT",
            borrowing=self.borrowing2,
            session_url="https://checkout.stripe.com/c/pay/cs_test1",
            session_id="cs_test1",
            money_to_pay=self.money_to_pay,
        )

    def test_list_all_payments(self):
        payments = Payment.objects.all()

        response = self.client.get(PAYMENT_URL)
        serializer = PaymentSerializer(payments, many=True)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data["results"], serializer.data)
