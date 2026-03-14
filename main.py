import logging

from services.config_loader import load_config
from clients.ozon_client import get_products, get_prices
from database.db import init_db, save_prices
from services.sku_cache import get_cached_sku, save_sku
from services.price_analyzer import analyze_prices
from services.telegram_notifier import send_telegram_alert


def main():

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    init_db()

    accounts = load_config()

    for acc in accounts:

        if acc["marketplace"] != "ozon":
            continue

        logging.info("Checking: %s", acc["name"])

        if not acc.get("client_id") or not acc.get("api_key"):
            logging.warning("API keys not set, skipping account")
            continue

        try:

            products = get_cached_sku(acc["name"])

            if not products:

                logging.info("Loading products from API...")

                products = get_products(
                    acc["client_id"],
                    acc["api_key"]
                )

                save_sku(acc["name"], products)

            else:
                logging.info("Products loaded from cache")

            logging.info("Products found: %s", len(products))

            prices = get_prices(
                acc["client_id"],
                acc["api_key"],
                products
            )

            logging.info("Prices loaded: %s", len(prices))

            # анализ изменений цен
            alerts = analyze_prices(
                acc["marketplace"],
                acc["name"],
                prices
            )

            if alerts:

                logging.warning("PRICE ALERTS FOUND: %s", len(alerts))

                for alert in alerts:

                    logging.info("Alert: %s", alert)

                    message = f"""
⚠ PRICE ALERT

Marketplace: {acc['marketplace']}
Account: {acc['name']}

SKU: {alert['sku']}

Old price: {alert['old_price']}
New price: {alert['new_price']}

Change: {alert['change']}%
Type: {alert['type']}
"""

                    send_telegram_alert(message)

            # сохраняем цены после анализа
            save_prices(
                acc["marketplace"],
                acc["name"],
                prices
            )

            logging.info("Prices saved to database")

        except Exception as e:
            logging.error("Account %s failed: %s", acc.get("name", "?"), e)
            continue


if __name__ == "__main__":
    main()