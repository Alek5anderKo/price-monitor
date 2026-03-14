from dotenv import load_dotenv
import os
import requests

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_IDS = os.getenv("TELEGRAM_CHAT_IDS", "").split(",")


def send_telegram_alert(message):

    if not TOKEN or not str(TOKEN).strip():
        return

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    for chat_id in CHAT_IDS:

        chat_id = chat_id.strip()

        if not chat_id:
            continue

        payload = {
            "chat_id": chat_id,
            "text": message
        }

        try:
            response = requests.post(
                url,
                json=payload,
                timeout=10
            )

            if response.status_code != 200:
                print("Telegram API error:", response.text)

        except requests.RequestException as e:
            print("Telegram request failed:", e)