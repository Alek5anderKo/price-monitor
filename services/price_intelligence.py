"""
Price Intelligence Layer (MVP). Reads price_history from SQLite only.
Produces analytics for the last N hours: top changes, active SKUs, anomaly flags.
"""
import sqlite3
from datetime import datetime, timedelta

from database.db import DB_NAME

REPORT_HOURS = 24
TOP_N = 10
SPREAD_PERCENT_THRESHOLD = 50  # flag if (max-min)/min * 100 > this
FREQUENCY_THRESHOLD = 10  # flag if record count per SKU in period > this


def _since_iso(hours):
    """Return ISO timestamp for N hours ago (for SQLite comparison)."""
    t = datetime.utcnow() - timedelta(hours=int(hours))
    return t.strftime("%Y-%m-%d %H:%M:%S")


def get_top_price_changes(hours=REPORT_HOURS, limit=TOP_N):
    """
    Returns list of (marketplace, account, sku, min_price, max_price, change_pct)
    for the period, ordered by absolute price change (largest first).
    """
    conn = sqlite3.connect(DB_NAME)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT marketplace, account, sku,
                   MIN(price) AS min_p, MAX(price) AS max_p,
                   COUNT(*) AS cnt
            FROM price_history
            WHERE created_at >= ?
            GROUP BY marketplace, account, sku
            HAVING min_p > 0 AND (MAX(price) - MIN(price)) > 0
            ORDER BY (MAX(price) - MIN(price)) DESC
            LIMIT ?
        """, (_since_iso(hours), limit))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            marketplace, account, sku, min_p, max_p, _ = r
            change_pct = round((max_p - min_p) / min_p * 100, 2)
            result.append({
                "marketplace": marketplace,
                "account": account,
                "sku": sku,
                "min_price": min_p,
                "max_price": max_p,
                "change_pct": change_pct,
            })
        return result
    finally:
        conn.close()


def get_most_active_skus(hours=REPORT_HOURS, limit=TOP_N):
    """
    Returns list of (marketplace, account, sku, record_count) for the period,
    ordered by record count descending (most price records = most active).
    """
    conn = sqlite3.connect(DB_NAME)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT marketplace, account, sku, COUNT(*) AS cnt
            FROM price_history
            WHERE created_at >= ?
            GROUP BY marketplace, account, sku
            ORDER BY cnt DESC
            LIMIT ?
        """, (_since_iso(hours), limit))
        rows = cursor.fetchall()
        return [
            {"marketplace": r[0], "account": r[1], "sku": r[2], "count": r[3]}
            for r in rows
        ]
    finally:
        conn.close()


def get_anomalies(hours=REPORT_HOURS):
    """
    Returns list of anomaly descriptions: large price spread or unusually
    frequent price changes in the period.
    """
    conn = sqlite3.connect(DB_NAME)
    try:
        cursor = conn.cursor()
        anomalies = []

        # Large spread: (max - min) / min * 100 > threshold
        cursor.execute("""
            SELECT marketplace, account, sku, MIN(price), MAX(price), COUNT(*)
            FROM price_history
            WHERE created_at >= ?
            GROUP BY marketplace, account, sku
            HAVING MIN(price) > 0
        """, (_since_iso(hours),))
        for r in cursor.fetchall():
            marketplace, account, sku, min_p, max_p, cnt = r
            spread_pct = (max_p - min_p) / min_p * 100
            if spread_pct >= SPREAD_PERCENT_THRESHOLD:
                anomalies.append({
                    "type": "large_spread",
                    "marketplace": marketplace,
                    "account": account,
                    "sku": sku,
                    "spread_pct": round(spread_pct, 2),
                    "min_price": min_p,
                    "max_price": max_p,
                })
            if cnt >= FREQUENCY_THRESHOLD:
                anomalies.append({
                    "type": "frequent_changes",
                    "marketplace": marketplace,
                    "account": account,
                    "sku": sku,
                    "record_count": cnt,
                })
        return anomalies
    finally:
        conn.close()
