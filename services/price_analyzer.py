import sqlite3
from datetime import datetime

from database.db import DB_NAME


def get_last_price(marketplace, account, sku):

    conn = sqlite3.connect(DB_NAME)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT price
            FROM price_history
            WHERE marketplace = ?
            AND account = ?
            AND sku = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (marketplace, account, sku))
        row = cursor.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def get_day_start_price(marketplace, account, sku):

    today = datetime.now().strftime("%Y-%m-%d")

    conn = sqlite3.connect(DB_NAME)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT price
            FROM price_history
            WHERE marketplace = ?
            AND account = ?
            AND sku = ?
            AND date(created_at) = ?
            ORDER BY created_at ASC
            LIMIT 1
        """, (marketplace, account, sku, today))
        row = cursor.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def analyze_prices(marketplace, account, prices):

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

        last_price = get_last_price(marketplace, account, sku)
        day_start_price = get_day_start_price(marketplace, account, sku)

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