import logging
import os
from datetime import datetime

from dotenv import load_dotenv

from services.daily_report import generate_daily_report_text
from services.email_notifier import send_email


def _bool_env(name, default=False):
    v = os.getenv(name)
    if v is None:
        return default
    return str(v).strip().lower() in ("true", "1", "yes", "on")


def _setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def main():
    load_dotenv()
    _setup_logging()

    report_date = datetime.now().strftime("%Y-%m-%d")
    report_text = generate_daily_report_text(report_date=report_date)
    logging.info("Daily report generated for date %s", report_date)

    if not _bool_env("SEND_DAILY_REPORT_EMAIL", False):
        logging.info("SEND_DAILY_REPORT_EMAIL=false; report was generated but not sent")
        return

    sent = send_email(f"Daily Report {report_date}", report_text)
    if sent:
        logging.info("Daily report email sent")
    else:
        logging.warning("Daily report email was not delivered")


if __name__ == "__main__":
    main()
