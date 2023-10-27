import decimal
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

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


class UnauthenticatedBorrowingsApiTests(APITestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(BORROWING_URL)
        self.assertEquals(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedBorrowingApiTests(APITestCase):
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

    @patch("borrowings.views.create_stripe_session_and_payment")
    def test_borrowing_return_overdue(self, mock_data):
        mock_data.return_value = MagicMock(url="testtest")
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
        response2 = self.client.post(url)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data["status"], "Session url has been updated")
        self.assertEquals(response2.data["status"], "Session url is still active")

    def test_filter_borrowings_is_active_true_or_false(self):
        borrowing1 = Borrowing.objects.create(
            expected_return_date=datetime.now().date() + timedelta(days=10),
            book=self.book,
            user=self.user,
        )
        borrowing2 = Borrowing.objects.create(
            expected_return_date=datetime.now().date() + timedelta(days=10),
            actual_return_date=datetime.now().date() + timedelta(days=8),
            book=self.book,
            user=self.user,
        )
        borrowing3 = Borrowing.objects.create(
            expected_return_date=datetime.now().date() + timedelta(days=10),
            actual_return_date=datetime.now().date() + timedelta(days=7),
            book=self.book,
            user=self.user,
        )
        borrowing4 = Borrowing.objects.create(
            expected_return_date=datetime.now().date() + timedelta(days=10),
            book=self.book,
            user=self.user,
        )

        response1 = self.client.get(BORROWING_URL, data={"is_active": "True"})
        response2 = self.client.get(BORROWING_URL, data={"is_active": "False"})

        serializer1 = BorrowingSerializer(borrowing1)
        serializer2 = BorrowingSerializer(borrowing2)
        serializer3 = BorrowingSerializer(borrowing3)
        serializer4 = BorrowingSerializer(borrowing4)

        self.assertIn(serializer1.data, response1.data["results"])
        self.assertIn(serializer4.data, response1.data["results"])
        self.assertIn(serializer3.data, response2.data["results"])
        self.assertIn(serializer2.data, response2.data["results"])


class AdminBorrowingApiTests(APITestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@admin.com", "testpass", is_staff=True
        )
        self.user2 = get_user_model().objects.create_user(
            "testunique1@tests.com", "unique_password"
        )
        self.user3 = get_user_model().objects.create_user(
            "testunique3@tests.com", "unique_password"
        )
        self.book = sample_book()
        self.client.force_authenticate(self.user)

    def test_list_all_borrowings(self):
        borrowing1 = Borrowing.objects.create(
            expected_return_date=datetime.now().date() + timedelta(days=10),
            book=self.book,
            user=self.user2,
        )
        borrowing2 = Borrowing.objects.create(
            expected_return_date=datetime.now().date() + timedelta(days=10),
            book=self.book,
            user=self.user3,
        )

        response = self.client.get(BORROWING_URL)

        borrowings = Borrowing.objects.all()

        serializer = BorrowingSerializer(borrowings, many=True)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data["results"], serializer.data)

    def test_borrowing_detail_another_user(self):
        borrowing = Borrowing.objects.create(
            expected_return_date=datetime.now().date() + timedelta(days=10),
            book=self.book,
            user=self.user3,
        )

        url = detail_url(borrowing.id)

        response = self.client.get(url)

        serializer = BorrowingDetailSerializer(borrowing)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data, serializer.data)

    def test_filter_borrowing_by_user_id(self):
        borrowing1 = Borrowing.objects.create(
            expected_return_date=datetime.now().date() + timedelta(days=9),
            book=self.book,
            user=self.user2,
        )
        borrowing2 = Borrowing.objects.create(
            expected_return_date=datetime.now().date() + timedelta(days=10),
            book=self.book,
            user=self.user3,
        )
        user = self.user3

        response = self.client.get(BORROWING_URL, data={"user": f"{user.id}"})

        serializer1 = BorrowingSerializer(borrowing1)
        serializer2 = BorrowingSerializer(borrowing2)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertIn(serializer2.data, response.data["results"])
        self.assertNotIn(serializer1.data, response.data["results"])

    def test_filter_borrowings_is_active_true_or_false(self):
        borrowing1 = Borrowing.objects.create(
            expected_return_date=datetime.now().date() + timedelta(days=9),
            book=self.book,
            user=self.user2,
        )
        borrowing2 = Borrowing.objects.create(
            expected_return_date=datetime.now().date() + timedelta(days=10),
            actual_return_date=datetime.now().date() + timedelta(days=7),
            book=self.book,
            user=self.user2,
        )
        borrowing3 = Borrowing.objects.create(
            expected_return_date=datetime.now().date() + timedelta(days=10),
            actual_return_date=datetime.now().date() + timedelta(days=8),
            book=self.book,
            user=self.user3,
        )
        borrowing4 = Borrowing.objects.create(
            expected_return_date=datetime.now().date() + timedelta(days=9),
            book=self.book,
            user=self.user3,
        )

        response1 = self.client.get(BORROWING_URL, data={"is_active": "True"})
        response2 = self.client.get(BORROWING_URL, data={"is_active": "False"})

        borrowings_active_true = Borrowing.objects.filter(
            actual_return_date__isnull=True
        )
        borrowings_active_false = Borrowing.objects.filter(
            actual_return_date__isnull=False
        )

        serializer_active_true_borrowings = BorrowingSerializer(
            borrowings_active_true, many=True
        )
        serializer_active_false_borrowings = BorrowingSerializer(
            borrowings_active_false, many=True
        )

        self.assertEquals(
            response1.data["results"], serializer_active_true_borrowings.data
        )
        self.assertEquals(
            response2.data["results"], serializer_active_false_borrowings.data
        )
