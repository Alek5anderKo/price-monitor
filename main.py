import logging
import logging.handlers
import os
import sys
from datetime import datetime

from services.config_loader import load_config
from services.config_validator import validate_configuration
from clients.ozon_client import get_products, get_prices
from database.db import init_db, save_prices
from services.sku_cache import get_cached_sku, save_sku
from services.price_analyzer import analyze_prices
from services.telegram_notifier import send_telegram_alert
from services.alert_state import should_send_alert, update_alert_state
import services.run_lock as run_lock

MARKETPLACE_OZON = "ozon"
MARKETPLACE_WILDBERIES = "wildberries"
LOG_DIR = "logs"
LOG_FILE = "logs/price_monitor.log"
LOG_FORMAT = "%(asctime)s %(levelname)s %(message)s"
LOG_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
LOG_BACKUP_COUNT = 5


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

    _setup_logging()

    if not run_lock.acquire():
        logging.warning("Another run is active (lock file exists). Exiting.")
        sys.exit(1)

    try:
        init_db()

        accounts = load_config()
        validate_configuration(accounts)
        DRY_RUN = os.getenv("DRY_RUN", "false").strip().lower() in ("true", "1", "yes")
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
            try:
                startup_msg = (
                    "Price Monitor started\n"
                    "Time: %s\n"
                    "Accounts configured: %s"
                ) % (datetime.now().strftime("%Y-%m-%d %H:%M"), len(accounts))
                send_telegram_alert(startup_msg)
            except Exception as e:
                logging.error("Startup Telegram notification failed: %s", e)

        for acc in accounts:

            marketplace = acc.get("marketplace")
            name = acc.get("name")
            if marketplace == MARKETPLACE_WILDBERIES:
                logging.info(
                    "Account %s (%s) is configured but Wildberries client is not implemented yet, skipping",
                    name,
                    marketplace,
                )
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
                        send_telegram_alert(message)
                        update_alert_state(marketplace, name, sku, new_price)
                        stats["alerts_sent_total"] += 1

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
        send_run_summary = os.getenv("SEND_RUN_SUMMARY", "false").strip().lower() in ("true", "1", "yes")
        if send_run_summary and not DRY_RUN:
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
        run_lock.release()


if __name__ == "__main__":
    main()