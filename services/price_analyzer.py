from datetime import datetime

from database.db import get_last_prices_bulk, get_day_start_prices_bulk


def analyze_prices(marketplace, account, prices):

    if not prices:
        return []

    today = datetime.now().strftime("%Y-%m-%d")
    last_prices = get_last_prices_bulk(marketplace, account)
    day_start_prices = get_day_start_prices_bulk(marketplace, account, today)

    alerts = []

    for item in prices:

        sku = item.get("sku")
        current_price = item.get("price")
        if sku is None or current_price is None:
            continue
        try:
            current_price = float(current_price)
        except (TypeError, ValueError):
            continue

        last_price = last_prices.get(sku)
        day_start_price = day_start_prices.get(sku)

        if last_price is None or day_start_price is None or last_price == 0 or day_start_price == 0:
            continue

        change_last = (current_price - last_price) / last_price * 100
        change_day = (current_price - day_start_price) / day_start_price * 100

        # изменение относительно последней цены
        if abs(change_last) > 1:

            alerts.append({
                "type": "last_price",
                "sku": sku,
                "old_price": last_price,
                "new_price": current_price,
                "change": round(change_last, 2)
            })

        # изменение относительно начала дня
        if abs(change_day) > 1:

            alerts.append({
                "type": "day_start",
                "sku": sku,
                "old_price": day_start_price,
                "new_price": current_price,
                "change": round(change_day, 2)
            })

    return alerts