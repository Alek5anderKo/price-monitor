from services.config_loader import load_config
from clients.ozon_client import get_products, get_prices
from database.db import init_db, save_prices
from services.sku_cache import get_cached_sku, save_sku
from services.price_analyzer import analyze_prices
from services.telegram_notifier import send_telegram_alert


def main():

    init_db()

    accounts = load_config()

    for acc in accounts:

        if acc["marketplace"] != "ozon":
            continue

        print(f"Checking: {acc['name']}")

        if not acc.get("client_id") or not acc.get("api_key"):
            print("API keys not set, skipping account")
            continue

        try:

            products = get_cached_sku(acc["name"])

            if not products:

                print("Loading products from API...")

                products = get_products(
                    acc["client_id"],
                    acc["api_key"]
                )

                save_sku(acc["name"], products)

            else:
                print("Products loaded from cache")

            print(f"Products found: {len(products)}")

            prices = get_prices(
                acc["client_id"],
                acc["api_key"],
                products
            )

            print(f"Prices loaded: {len(prices)}")

            # анализ изменений цен
            alerts = analyze_prices(
                acc["marketplace"],
                acc["name"],
                prices
            )

            if alerts:

                print("PRICE ALERTS FOUND:")

                for alert in alerts:

                    print(alert)

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

            print("Prices saved to database")

        except Exception as e:
            print(f"Account {acc.get('name', '?')} failed: {e}")
            continue


if __name__ == "__main__":
    main()