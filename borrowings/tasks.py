from celery import shared_task

from borrowings.utils import borrowing_overdue_send_message, check_borrowings_overdue


@shared_task
def daily_borrowings_overdue_notification():
    borrowing_overdue_send_message(check_borrowings_overdue())
