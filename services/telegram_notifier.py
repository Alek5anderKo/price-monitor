import logging
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_IDS = os.getenv("TELEGRAM_CHAT_IDS", "").split(",")

logger = logging.getLogger(__name__)

API_TIMEOUT = 10
MAX_RETRIES = 3
RETRY_DELAY = 2


def send_telegram_alert(message):

    if not TOKEN or not str(TOKEN).strip():
        logger.warning("Telegram token is not configured")
        return False

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    overall_success = False
    for chat_id in CHAT_IDS:

        chat_id = chat_id.strip()

        if not chat_id:
            continue

        payload = {
            "chat_id": chat_id,
            "text": message
        }

        sent = False
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = requests.post(
                    url,
                    json=payload,
                    timeout=API_TIMEOUT,
                )

                if response.ok:
                    logger.info("Telegram message sent to chat_id=%s", chat_id)
                    sent = True
                    overall_success = True
                    break

                logger.error(
                    "Telegram send failed for chat_id=%s attempt=%s status=%s response=%s",
                    chat_id,
                    attempt,
                    response.status_code,
                    response.text,
                )
            except requests.RequestException as e:
                logger.error(
                    "Telegram request failed for chat_id=%s attempt=%s: %s",
                    chat_id,
                    attempt,
                    e,
                )

            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

        if not sent:
            logger.error(
                "Telegram message was not delivered to chat_id=%s after all retries",
                chat_id,
            )

    return overall_success