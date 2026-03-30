import logging
import logging.handlers
import os
import sys
from datetime import datetime

from services.config_loader import load_config
from services.config_validator import validate_configuration
from clients.ozon_client import get_products, get_prices
from clients.wb_client import get_products as wb_get_products, get_prices as wb_get_prices
from database.db import init_db, save_prices
from services.sku_cache import get_cached_sku, save_sku
from services.price_analyzer import analyze_prices
from services.telegram_notifier import send_telegram_alert
from services.email_notifier import send_email
from services.alert_state import should_send_alert, update_alert_state
from services.run_lock import acquire_lock, release_lock

MARKETPLACE_OZON = "ozon"
MARKETPLACE_WILDBERIES = "wildberries"
LOG_DIR = "logs"
LOG_FILE = "logs/price_monitor.log"
LOG_FORMAT = "%(asctime)s %(levelname)s %(message)s"
LOG_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
LOG_BACKUP_COUNT = 5


def _bool_env(name, default=False):
    v = os.getenv(name)
    if v is None:
        return default
    return str(v).strip().lower() in ("true", "1", "yes", "on")


def _setup_logging():
    os.makedirs(LOG_DIR, exist_ok=True)
    formatter = logging.Formatter(LOG_FORMAT)
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(file_handler)
    root.addHandler(stream_handler)


def main():

    acquire_lock()
    _setup_logging()

    try:
        init_db()

        accounts = load_config()
        validate_configuration(accounts)
        DRY_RUN = _bool_env("DRY_RUN", False)
        SEND_TELEGRAM_ALERTS = _bool_env("SEND_TELEGRAM_ALERTS", True)
        SEND_EMAIL_ALERTS = _bool_env("SEND_EMAIL_ALERTS", False)
        SEND_STARTUP_MESSAGE = _bool_env("SEND_STARTUP_MESSAGE", False)
        SEND_STARTUP_EMAIL = _bool_env("SEND_STARTUP_EMAIL", False)
        EMAIL_TO_ALERTS = os.getenv("EMAIL_TO_ALERTS") or ""
        if not str(EMAIL_TO_ALERTS).strip():
            EMAIL_TO_ALERTS = os.getenv("EMAIL_TO") or ""
        if DRY_RUN:
            logging.info("DRY RUN enabled")
        stats = {
            "accounts_total": len(accounts),
            "accounts_processed": 0,
            "accounts_skipped": 0,
            "prices_fetched_total": 0,
            "alerts_detected_total": 0,
            "alerts_sent_total": 0,
            "alerts_suppressed_total": 0,
        }

        if accounts and not DRY_RUN:
            startup_msg = (
                "Price Monitor started\n"
                "Time: %s\n"
                "Accounts configured: %s"
            ) % (datetime.now().strftime("%Y-%m-%d %H:%M"), len(accounts))
            if SEND_STARTUP_MESSAGE:
                try:
                    send_telegram_alert(startup_msg)
                except Exception as e:
                    logging.error("Startup Telegram notification failed: %s", e)
            if SEND_STARTUP_EMAIL:
                try:
                    send_email("Price Monitor Started", startup_msg)
                except Exception as e:
                    logging.error("Startup email notification failed: %s", e)

        for acc in accounts:

            marketplace = acc.get("marketplace")
            name = acc.get("name")
            if marketplace == MARKETPLACE_WILDBERIES:
                if not acc.get("api_key"):
                    logging.warning("Wildberries account %s: api_key missing in .env; skipping", name)
                    stats["accounts_skipped"] += 1
                    continue
                logging.info("Checking: %s (Wildberries)", name)
                try:
                    products = wb_get_products(acc["api_key"])
                    logging.info("Products found: %s", len(products))
                    if not products:
                        logging.warning("Account %s (%s) returned 0 products", name, marketplace)
                    prices = wb_get_prices(acc["api_key"], products)
                    logging.info("Prices loaded: %s", len(prices))
                    stats["prices_fetched_total"] += len(prices) if prices else 0
                    if not prices:
                        logging.warning("Account %s (%s) returned 0 prices", name, marketplace)
                    alerts = analyze_prices(marketplace, name, prices)
                    if alerts:
                        stats["alerts_detected_total"] += len(alerts)
                        logging.warning("PRICE ALERTS FOUND: %s", len(alerts))
                        for alert in alerts:
                            logging.info("Alert: %s", alert)
                            sku = alert["sku"]
                            new_price = alert["new_price"]
                            if not should_send_alert(marketplace, name, sku, new_price):
                                stats["alerts_suppressed_total"] += 1
                                continue
                            if DRY_RUN:
                                logging.info("DRY RUN: alert detected but not sent")
                                continue
                            message = f"""
⚠ PRICE ALERT

Marketplace: {marketplace}
Account: {name}

SKU: {sku}

Old price: {alert['old_price']}
New price: {new_price}

Change: {alert['change']}%
Type: {alert['type']}
"""
                            sent_any = False
                            if SEND_TELEGRAM_ALERTS:
                                if send_telegram_alert(message):
                                    sent_any = True
                            if SEND_EMAIL_ALERTS:
                                if send_email(
                                    f"ALERT {marketplace} / {name} / {sku}",
                                    message,
                                    recipients=EMAIL_TO_ALERTS,
                                ):
                                    sent_any = True
                            if sent_any:
                                update_alert_state(marketplace, name, sku, new_price)
                                stats["alerts_sent_total"] += 1
                            else:
                                logging.info("Alert was not delivered by enabled channels")
                    if not DRY_RUN:
                        save_prices(marketplace, name, prices)
                        logging.info("Prices saved to database")
                    else:
                        logging.info("DRY RUN: prices not saved to database")
                    stats["accounts_processed"] += 1
                except Exception as e:
                    logging.warning("Account %s (Wildberries) failed: %s", name, e)
                    stats["accounts_skipped"] += 1
                continue
            if marketplace != MARKETPLACE_OZON:
                logging.info("Skipping unsupported marketplace: %s (account %s)", marketplace, name)
                stats["accounts_skipped"] += 1
                continue
            if not name:
                stats["accounts_skipped"] += 1
                continue

            logging.info("Checking: %s", name)

            if not acc.get("client_id") or not acc.get("api_key"):
                logging.warning("API keys not set, skipping account")
                stats["accounts_skipped"] += 1
                continue

            try:

                products = get_cached_sku(name)

                if not products:

                    logging.info("Loading products from API...")

                    products = get_products(
                        acc["client_id"],
                        acc["api_key"]
                    )

                    save_sku(name, products)

                else:
                    logging.info("Products loaded from cache")

                logging.info("Products found: %s", len(products))
                if not products:
                    logging.warning("Account %s (%s) returned 0 products", name, marketplace)

                prices = get_prices(
                    acc["client_id"],
                    acc["api_key"],
                    products
                )

                logging.info("Prices loaded: %s", len(prices))
                stats["prices_fetched_total"] += len(prices) if prices else 0
                if not prices:
                    logging.warning("Account %s (%s) returned 0 prices", name, marketplace)

                # анализ изменений цен
                alerts = analyze_prices(marketplace, name, prices)

                if alerts:
                    stats["alerts_detected_total"] += len(alerts)
                    logging.warning("PRICE ALERTS FOUND: %s", len(alerts))

                    for alert in alerts:

                        logging.info("Alert: %s", alert)

                        sku = alert["sku"]
                        new_price = alert["new_price"]
                        if not should_send_alert(marketplace, name, sku, new_price):
                            stats["alerts_suppressed_total"] += 1
                            continue
                        if DRY_RUN:
                            logging.info("DRY RUN: alert detected but not sent")
                            continue
                        message = f"""
⚠ PRICE ALERT

Marketplace: {marketplace}
Account: {name}

SKU: {sku}

Old price: {alert['old_price']}
New price: {new_price}

Change: {alert['change']}%
Type: {alert['type']}
"""
                        sent_any = False
                        if SEND_TELEGRAM_ALERTS:
                            if send_telegram_alert(message):
                                sent_any = True
                        if SEND_EMAIL_ALERTS:
                            if send_email(
                                f"ALERT {marketplace} / {name} / {sku}",
                                message,
                                recipients=EMAIL_TO_ALERTS,
                            ):
                                sent_any = True
                        if sent_any:
                            update_alert_state(marketplace, name, sku, new_price)
                            stats["alerts_sent_total"] += 1
                        else:
                            logging.info("Alert was not delivered by enabled channels")

                # сохраняем цены после анализа
                if not DRY_RUN:
                    save_prices(marketplace, name, prices)
                    logging.info("Prices saved to database")
                else:
                    logging.info("DRY RUN: prices not saved to database")
                stats["accounts_processed"] += 1

            except Exception as e:
                logging.error("Account %s failed: %s", name, e)
                stats["accounts_skipped"] += 1
                continue

        logging.info(
            "Run summary: accounts_total=%s accounts_processed=%s accounts_skipped=%s "
            "prices_fetched=%s alerts_detected=%s alerts_sent=%s alerts_suppressed=%s",
            stats["accounts_total"],
            stats["accounts_processed"],
            stats["accounts_skipped"],
            stats["prices_fetched_total"],
            stats["alerts_detected_total"],
            stats["alerts_sent_total"],
            stats["alerts_suppressed_total"],
        )
        send_run_summary = _bool_env("SEND_RUN_SUMMARY", False)
        if send_run_summary and not DRY_RUN and SEND_TELEGRAM_ALERTS:
            try:
                summary_msg = (
                    "Price Monitor run completed\n\n"
                    "Accounts processed: %s\n"
                    "Prices fetched: %s\n"
                    "Alerts detected: %s\n"
                    "Alerts sent: %s\n"
                    "Alerts suppressed: %s"
                ) % (
                    stats["accounts_processed"],
                    stats["prices_fetched_total"],
                    stats["alerts_detected_total"],
                    stats["alerts_sent_total"],
                    stats["alerts_suppressed_total"],
                )
                send_telegram_alert(summary_msg)
            except Exception as e:
                logging.error("Run summary Telegram notification failed: %s", e)
        logging.info("Run completed")
    finally:
        release_lock()


if __name__ == "__main__":
    main()