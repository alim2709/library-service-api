import stripe
from celery import shared_task
from django.conf import settings
from django.db.models import QuerySet

from payments.models import Payment


stripe.api_key = settings.STRIPE_SECRET_KEY


def get_pending_payments() -> QuerySet:
    queryset = Payment.objects.filter(status="Pending").select_related("borrowing")
    return queryset


@shared_task
def track_expire_stripe_sessions() -> None:
    pending_payments = get_pending_payments()
    if pending_payments:
        for payment in pending_payments:
            session_id = payment.session_id
            session = stripe.checkout.Session.retrieve(session_id)
            if session.status == "expired":
                payment.status = "Expired"
                payment.save()
