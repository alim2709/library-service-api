import decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from books.models import Book
from books.serializers import BookListSerializer, BookSerializer

BOOK_URL = reverse("books:book-list")


def sample_book(**params):
    defaults = {
        "title": "test_title",
        "author": "test_author",
        "cover": "Soft",
        "inventory": 25,
        "daily_fee": decimal.Decimal(25),
    }
    defaults.update(params)
    return Book.objects.create(**defaults)


def detail_url(book_id):
    return reverse("books:book-detail", args=[book_id])


class UnauthenticatedBooksApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.book = sample_book()

    def test_list_books_auth_not_required(self):
        res = self.client.get(BOOK_URL)
        self.assertEquals(res.status_code, status.HTTP_200_OK)

    def test_create_book_not_allowed(self):
        payload = {
            "title": "test_title",
            "author": "test_author",
            "cover": "Soft",
            "inventory": 25,
            "daily_fee": decimal.Decimal(25),
        }
        response = self.client.post(BOOK_URL, payload)

        self.assertEquals(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_detail_book_allowed(self):
        book = sample_book()
        url = detail_url(book.id)

        response = self.client.get(url)

        self.assertEquals(response.status_code, status.HTTP_200_OK)


class AuthenticatedBookApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "testunique@tests.com", "unique_password"
        )
        self.client.force_authenticate(self.user)
        self.book = sample_book()

    def test_list_books(self):
        response = self.client.get(BOOK_URL)

        books = Book.objects.all()
        serializer = BookListSerializer(books, many=True)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data["results"], serializer.data)

    def test_retrieve_book_detail(self):
        book = self.book

        url = detail_url(book.id)
        res = self.client.get(url)

        serializer = BookSerializer(book)

        self.assertEquals(res.status_code, status.HTTP_200_OK)
        self.assertEquals(res.data, serializer.data)

    def test_book_create_book_not_allowed(self):
        payload = {
            "title": "test_title",
            "author": "test_author",
            "cover": "Soft",
            "inventory": 25,
            "daily_fee": decimal.Decimal(25),
        }
        response = self.client.post(BOOK_URL, payload)

        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_book_update_not_allowed(self):
        book = self.book

        url = detail_url(book.id)

        payload = {
            "title": "test_title_update",
            "author": "test_author_update",
            "cover": "Hard",
            "inventory": 26,
            "daily_fee": decimal.Decimal(30),
        }

        res = self.client.put(url, payload)

        self.assertEquals(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_book_delete_not_allowed(self):
        book = self.book

        url = detail_url(book.id)

        res = self.client.delete(url)

        self.assertEquals(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminBookApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@admin.com", "testpass", is_staff=True
        )
        self.client.force_authenticate(self.user)
        self.book = sample_book()

    def test_book_create(self):
        payload = {
            "title": "test_title_create",
            "author": "test_author_create",
            "cover": "Soft",
            "inventory": 100,
            "daily_fee": decimal.Decimal(100),
        }

        res = self.client.post(BOOK_URL, payload)
        serializer = BookSerializer(res.data, many=False)

        self.assertEquals(res.status_code, status.HTTP_201_CREATED)
        self.assertEquals(res.data, serializer.data)

    def test_book_update(self):
        book = self.book
        url = detail_url(book.id)

        payload = {
            "title": "test_title_create",
            "author": "test_author_create",
            "cover": "Soft",
            "inventory": 100,
            "daily_fee": decimal.Decimal(100),
        }

        res = self.client.put(url, payload)

        self.assertEquals(res.status_code, status.HTTP_200_OK)

    def test_book_delete(self):
        book = self.book
        url = detail_url(book.id)

        res = self.client.delete(url)

        self.assertEquals(res.status_code, status.HTTP_204_NO_CONTENT)
