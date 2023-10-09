from datetime import datetime, timedelta

from django.db.models import QuerySet

from borrowings.models import Borrowing
from borrowings.notifications import send_telegram_notification


def get_borrowing_info(borrowing: Borrowing) -> str:
    return (
        f"id: {borrowing.id}\n"
        f"Borrow date: {borrowing.borrow_date}\n"
        f"Expected return date: {borrowing.expected_return_date}\n"
        f"Book: {borrowing.book.title}\n"
        f"User info: {borrowing.user}\n"
        f"User id: {borrowing.user.id}"
    )


def check_borrowings_overdue() -> QuerySet:
    queryset = Borrowing.objects.select_related("user", "book").filter(
        actual_return_date__isnull=True,
        expected_return_date__lte=datetime.now().date() + timedelta(days=1),
    )
    return queryset


def borrowing_overdue_send_message(queryset: QuerySet):
    if not queryset:
        return send_telegram_notification("No borrowings overdue today!")

    for borrowing in queryset:
        send_telegram_notification(
            "Borrowing overdue:\n" + get_borrowing_info(borrowing)
        )


def daily_borrowings_overdue_notification():
    borrowing_overdue_send_message(check_borrowings_overdue())
