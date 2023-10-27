import requests
from django.conf import settings
from rest_framework.response import Response

TELEGRAM_BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID = settings.TELEGRAM_CHAT_ID
URL = settings.URL_NOTIFICATION


def send_telegram_notification(message: str) -> Response:
    req_info = requests.post(URL, json={"chat_id": TELEGRAM_CHAT_ID, "text": message})

    return req_info
