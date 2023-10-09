from payments.models import Payment


def get_payment_info(payment: Payment) -> str:
    info = (
        f"id: {payment.id}\n"
        f"Type: {payment.type}\n"
        f"Borrowed book: {payment.borrowing.book.title}\n"
        f"Money paid: {payment.money_to_pay}$\n"
        f"User: {payment.borrowing.user}"
    )
    return info
