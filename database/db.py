import sqlite3


DB_NAME = "prices.db"


def init_db():

    conn = sqlite3.connect(DB_NAME)
    try:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            marketplace TEXT,
            account TEXT,
            sku TEXT,
            product_id INTEGER,
            price REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_price_history_lookup
        ON price_history(marketplace, account, sku, created_at)
        """)
        conn.commit()
    finally:
        conn.close()


def get_last_prices_bulk(marketplace, account):
    """Возвращает словарь sku -> последняя цена по каждому SKU для marketplace/account."""
    conn = sqlite3.connect(DB_NAME)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ph.sku, ph.price
            FROM price_history ph
            INNER JOIN (
                SELECT marketplace, account, sku, MAX(created_at) AS max_ts
                FROM price_history
                WHERE marketplace = ? AND account = ?
                GROUP BY marketplace, account, sku
            ) t ON ph.marketplace = t.marketplace AND ph.account = t.account
                AND ph.sku = t.sku AND ph.created_at = t.max_ts
            WHERE ph.marketplace = ? AND ph.account = ?
        """, (marketplace, account, marketplace, account))
        return {row[0]: row[1] for row in cursor.fetchall()}
    finally:
        conn.close()


def get_day_start_prices_bulk(marketplace, account, date_str):
    """Возвращает словарь sku -> цена на начало дня date_str по каждому SKU."""
    conn = sqlite3.connect(DB_NAME)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ph.sku, ph.price
            FROM price_history ph
            INNER JOIN (
                SELECT marketplace, account, sku, MIN(created_at) AS min_ts
                FROM price_history
                WHERE marketplace = ? AND account = ? AND date(created_at) = ?
                GROUP BY marketplace, account, sku
            ) t ON ph.marketplace = t.marketplace AND ph.account = t.account
                AND ph.sku = t.sku AND ph.created_at = t.min_ts
            WHERE ph.marketplace = ? AND ph.account = ? AND date(ph.created_at) = ?
        """, (marketplace, account, date_str, marketplace, account, date_str))
        return {row[0]: row[1] for row in cursor.fetchall()}
    finally:
        conn.close()


def _is_valid_price_item(item):
    """Проверка, что запись пригодна для сохранения в price_history."""
    if not isinstance(item, dict):
        return False
    if "sku" not in item or "product_id" not in item or "price" not in item:
        return False
    price = item["price"]
    if price is None:
        return False
    try:
        p = float(price)
    except (TypeError, ValueError):
        return False
    return p >= 0


def save_prices(marketplace, account, prices):

    if not prices:
        return

    rows = [
        (marketplace, account, item["sku"], item["product_id"], item["price"])
        for item in prices
        if _is_valid_price_item(item)
    ]
    if not rows:
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.executemany("""
            INSERT INTO price_history
            (marketplace, account, sku, product_id, price)
            VALUES (?, ?, ?, ?, ?)
        """, rows)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()