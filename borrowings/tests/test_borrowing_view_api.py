import decimal
from unittest.mock import patch
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient


from books.models import Book
from books.tests.test_book_api import sample_book
from borrowings.models import Borrowing
from borrowings.serializers import (
    BorrowingSerializer,
    BorrowingDetailSerializer,
)
from payments.models import Payment

BORROWING_URL = reverse("borrowings:borrowing-list")


def detail_url(borrowing_id):
    return reverse("borrowings:borrowing-detail", args=[borrowing_id])


class UnauthenticatedBooksApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(BORROWING_URL)
        self.assertEquals(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedBookApiTests(TestCase):
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
            expected_return_date=datetime.now().date() + timedelta(days=7),
            book=self.book,
            user=self.user,
        )
        self.borrowing2 = Borrowing.objects.create(
            expected_return_date=datetime.now().date() + timedelta(days=8),
            book=self.book,
            user=self.user2,
        )

    def test_list_borrowings(self):
        response = self.client.get(BORROWING_URL)
        borrowings = Borrowing.objects.all()
        serializer = BorrowingSerializer(borrowings, many=True)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertNotEquals(response.data["results"], serializer.data)

    def test_retrieve_own_borrowing_detail(self):
        borrowing_user = self.borrowing
        borrowing_user2 = self.borrowing2

        borrowing_user_url = detail_url(borrowing_user.id)
        borrowing_user2_url = detail_url(borrowing_user2.id)

        response1 = self.client.get(borrowing_user_url)
        response2 = self.client.get(borrowing_user2_url)

        serializer = BorrowingDetailSerializer(borrowing_user)

        self.assertEquals(response1.status_code, status.HTTP_200_OK)
        self.assertEquals(response1.data, serializer.data)
        self.assertEquals(response2.status_code, status.HTTP_404_NOT_FOUND)

    @patch("borrowings.serializers.send_telegram_notification")
    def test_borrowing_create(self, mock_data):
        book = self.book
        data = {
            "expected_return_date": datetime.now().date() + timedelta(days=8),
            "book": book.id,
        }

        response = self.client.post(BORROWING_URL, data=data)
        book_inventory_after_borrowing = Book.objects.get(id=book.id).inventory

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        self.assertEquals(book_inventory_after_borrowing, 24)

    def test_borrowing_create_not_allowed_if_previous_not_payed(self):
        Payment.objects.create(
            status="Pending",
            type="Payment",
            borrowing=self.borrowing,
            money_to_pay=decimal.Decimal(25),
        )

        book = self.book
        data = {
            "expected_return_date": datetime.now().date() + timedelta(days=8),
            "book": book.id,
        }

        response = self.client.post(BORROWING_URL, data=data)

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEquals(
            response.data["non_field_errors"][0],
            "You have one or more pending payments. You can't make borrowings until you pay for them.",
        )

    def test_borrowing_return(self):
        borrowing = self.borrowing

        url = detail_url(borrowing.id) + "borrowing_return/"

        response = self.client.post(url)
        response2 = self.client.post(url)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data["status"], "borrowing returned")
        self.assertEquals(
            response2.data["non_field_errors"][0],
            "Borrowing has been already returned.",
        )

    # @patch(
    #     "borrowings.views.BorrowingViewSet.borrowing_return.create_stripe_session_and_payment"
    # )
    def test_borrowing_return_overdue(self):
        borrowing = Borrowing.objects.create(
            expected_return_date=datetime.now().date() - timedelta(days=2),
            book=self.book,
            user=self.user,
        )

        url = detail_url(borrowing.id) + "borrowing_return/"

        response = self.client.post(url)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(
            response.data["message"],
            "Your return is overdue please provide Fine payment",
        )

    def test_update_expired_borrowing_session_url_and_sesion_id(self):
        Payment.objects.create(
            status="Expired",
            type="Payment",
            borrowing=self.borrowing,
            money_to_pay=decimal.Decimal(25),
        )

        url = detail_url(self.borrowing.id) + "update_session_url/"

        response = self.client.post(url)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data["status"], "Session url has been updated")
