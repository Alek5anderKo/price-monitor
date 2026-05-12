import logging
import os
import re
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

from clients.ozon_orders_client import get_ozon_orders_for_period
from clients.ozon_stock_client import get_ozon_stocks
from services.config_loader import load_config
from services.email_notifier import send_email
from services.run_lock import acquire_lock, release_lock
from services.sales_drop_analyzer import detect_sales_drop_alerts
from services.sales_drop_email_report import build_sales_drop_email_text

ALLOWED_OZON_ACCOUNTS = {"ozon_1", "ozon_2"}


def _setup_logging():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def _bool_env(name, default=False):
    v = os.getenv(name)
    if v is None:
        return default
    return str(v).strip().lower() in ("true", "1", "yes", "on")


def _int_env(name, default):
    try:
        v = os.getenv(name)
        if v is None or str(v).strip() == "":
            return int(default)
        return int(v)
    except (TypeError, ValueError):
        return int(default)


def _float_env(name, default):
    try:
        v = os.getenv(name)
        if v is None or str(v).strip() == "":
            return float(default)
        return float(v)
    except (TypeError, ValueError):
        return float(default)


def _normalize_account_id(name):
    raw = str(name or "").strip().lower()
    raw = raw.replace("#", "_")
    raw = re.sub(r"[^a-z0-9]+", "_", raw)
    return raw.strip("_")


def _weekly_periods():
    # Exclude current partial day to avoid false drops.
    today_utc = datetime.now(timezone.utc).date()
    current_end = today_utc - timedelta(days=1)
    current_start = current_end - timedelta(days=6)
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=6)

    current_from = datetime.combine(current_start, datetime.min.time(), tzinfo=timezone.utc)
    current_to = datetime.combine(current_end, datetime.max.time(), tzinfo=timezone.utc)
    prev_from = datetime.combine(previous_start, datetime.min.time(), tzinfo=timezone.utc)
    prev_to = datetime.combine(previous_end, datetime.max.time(), tzinfo=timezone.utc)
    return (current_from, current_to), (prev_from, prev_to), current_end


def main():
    load_dotenv()
    _setup_logging()
    lock_path = os.path.join("locks", "sales_drop.lock")
    try:
        acquire_lock(lock_path)

        if not _bool_env("SALES_DROP_ENABLED", False):
            logging.info("SALES_DROP_ENABLED=false; sales drop report skipped")
            return

        accounts = load_config()
        strong_drop_factor = _float_env("SALES_DROP_STRONG_DROP_FACTOR", 3)
        min_prev_orders = _int_env("SALES_DROP_MIN_PREVIOUS_WEEK_ORDERS", 10)
        stopped_min_prev_orders = _int_env("SALES_DROP_STOPPED_MIN_PREVIOUS_WEEK_ORDERS", 5)
        (current_from, current_to), (prev_from, prev_to), report_date = _weekly_periods()
        logging.info(
            "Sales drop periods: current_7_days=%s..%s previous_7_days=%s..%s",
            current_from.date().isoformat(),
            current_to.date().isoformat(),
            prev_from.date().isoformat(),
            prev_to.date().isoformat(),
        )

        source_rows = []

        for acc in accounts:
            marketplace = acc.get("marketplace")
            name = acc.get("name")
            account_id = _normalize_account_id(name)
            if marketplace != "ozon" or account_id not in ALLOWED_OZON_ACCOUNTS:
                continue

            client_id = acc.get("client_id")
            api_key = acc.get("api_key")
            stocks = get_ozon_stocks(client_id, api_key)
            current_orders = get_ozon_orders_for_period(client_id, api_key, current_from, current_to)
            previous_orders = get_ozon_orders_for_period(client_id, api_key, prev_from, prev_to)
            logging.info(
                "Sales drop source loaded: account=%s stock_rows=%s current_orders_rows=%s previous_orders_rows=%s",
                name,
                len(stocks),
                len(current_orders),
                len(previous_orders),
            )

            for stock_item in stocks:
                sku = str(stock_item.get("sku"))
                source_rows.append(
                    {
                        "marketplace": "ozon",
                        "account": name,
                        "sku": sku,
                        "product_id": stock_item.get("product_id"),
                        "current_stock": int(stock_item.get("current_stock", 0) or 0),
                        "current_7_orders": int(current_orders.get(sku, 0) or 0),
                        "previous_7_orders": int(previous_orders.get(sku, 0) or 0),
                    }
                )

        alerts = detect_sales_drop_alerts(
            source_rows,
            strong_drop_factor=strong_drop_factor,
            min_prev_orders=min_prev_orders,
            stopped_min_prev_orders=stopped_min_prev_orders,
        )
        logging.info("sales_drop_alerts_found=%s", len(alerts))
        if not alerts:
            logging.info("No sales drop alerts found; email not sent")
            return

        recipients = os.getenv("SALES_DROP_EMAILS")
        if recipients is not None and str(recipients).strip() == "":
            recipients = None

        email_text = build_sales_drop_email_text(alerts)
        subject_date = report_date.strftime("%d.%m.%Y")
        sent = send_email(f"Снижение продаж за {subject_date}", email_text, recipients=recipients)
        if sent:
            logging.info("Sales drop email sent")
        else:
            logging.warning("Sales drop email was not delivered")

    finally:
        release_lock(lock_path)


if __name__ == "__main__":
    main()
