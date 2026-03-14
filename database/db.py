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
        CREATE INDEX IF NOT EXISTS idx_price_lookup
        ON price_history(marketplace, account, sku, created_at)
        """)
        conn.commit()
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

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        for item in prices:
            if not _is_valid_price_item(item):
                continue
            cursor.execute("""
                INSERT INTO price_history
                (marketplace, account, sku, product_id, price)
                VALUES (?, ?, ?, ?, ?)
            """, (
                marketplace,
                account,
                item["sku"],
                item["product_id"],
                item["price"]
            ))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()