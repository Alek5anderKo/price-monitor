import logging
import os
from datetime import datetime

from dotenv import load_dotenv

from database.db import get_last_prices_bulk, get_day_start_prices_bulk

load_dotenv()

logger = logging.getLogger(__name__)


def _float_env(name, default):
    """Read float from env; on missing or invalid value return default."""
    try:
        v = os.getenv(name)
        if v is None or str(v).strip() == "":
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


LAST_PRICE_ALERT_THRESHOLD_PERCENT = _float_env("LAST_PRICE_ALERT_THRESHOLD_PERCENT", 10.0)
DAY_START_ALERT_THRESHOLD_PERCENT = _float_env("DAY_START_ALERT_THRESHOLD_PERCENT", 20.0)
MAX_ALERT_CHANGE_PERCENT = _float_env("MAX_ALERT_CHANGE_PERCENT", 100.0)


def analyze_prices(marketplace, account, prices):

    if not prices:
        return []

    today = datetime.now().strftime("%Y-%m-%d")
    last_prices = get_last_prices_bulk(marketplace, account)
    day_start_prices = get_day_start_prices_bulk(marketplace, account, today)

    alerts = []

    for item in prices:

        sku = str(item.get("sku")) if item.get("sku") is not None else None
        current_price = item.get("price")
        if sku is None or current_price is None:
            continue
        try:
            current_price = float(current_price)
        except (TypeError, ValueError):
            continue
        if current_price <= 0:
            continue

        last_price = last_prices.get(sku)
        day_start_price = day_start_prices.get(sku)

        if last_price is None or day_start_price is None or last_price == 0 or day_start_price == 0:
            logger.debug(
                "Skipping SKU %s: last_price=%s day_start_price=%s",
                sku,
                last_price,
                day_start_price,
            )
            continue

        change_last = (current_price - last_price) / last_price * 100
        change_day = (current_price - day_start_price) / day_start_price * 100

        # изменение относительно последней цены
        if LAST_PRICE_ALERT_THRESHOLD_PERCENT < abs(change_last) <= MAX_ALERT_CHANGE_PERCENT:
            alerts.append({
                "type": "last_price",
                "sku": sku,
                "old_price": last_price,
                "new_price": current_price,
                "change": round(change_last, 2)
            })

        # изменение относительно начала дня
        if DAY_START_ALERT_THRESHOLD_PERCENT < abs(change_day) <= MAX_ALERT_CHANGE_PERCENT:
            alerts.append({
                "type": "day_start",
                "sku": sku,
                "old_price": day_start_price,
                "new_price": current_price,
                "change": round(change_day, 2)
            })

    return alerts