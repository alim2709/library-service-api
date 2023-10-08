from borrowings.models import Borrowing


def get_borrowing_info(borrowing: Borrowing) -> str:
    return (
        f"id: {borrowing.id}\n"
        f"Borrow date: {borrowing.borrow_date}\n"
        f"Expected return date: {borrowing.expected_return_date}\n"
        f"Book: {borrowing.book.title}\n"
        f"User info: {borrowing.user}\n"
        f"User id: {borrowing.user.id}"
    )
