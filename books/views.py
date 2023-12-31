import rest_framework_simplejwt.authentication
from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser, AllowAny

from books.models import Book
from books.serializers import BookSerializer, BookListSerializer


class BookViewSet(viewsets.ModelViewSet):
    """Endpoint for CRUD operations with book"""

    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = (IsAdminUser,)
    authentication_classes = (
        rest_framework_simplejwt.authentication.JWTAuthentication,
    )

    def get_serializer_class(self):
        if self.action == "list":
            return BookListSerializer
        return BookSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        return super().get_permissions()
