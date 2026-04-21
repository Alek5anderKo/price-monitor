import sqlite3
from datetime import datetime

from database.db import DB_NAME


def _normalize_report_date(report_date=None):
    if report_date is None:
        return datetime.now().strftime("%Y-%m-%d")
    if hasattr(report_date, "strftime"):
        return report_date.strftime("%Y-%m-%d")
    return str(report_date)


def _get_day_stats(conn, date_str):
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            COUNT(*) AS total_records,
            COUNT(DISTINCT sku) AS unique_skus,
            COUNT(DISTINCT account) AS unique_accounts
        FROM price_history
        WHERE date(created_at) = ?
        """,
        (date_str,),
    )
    row = cursor.fetchone() or (0, 0, 0)
    return {
        "total_records": int(row[0] or 0),
        "unique_skus": int(row[1] or 0),
        "unique_accounts": int(row[2] or 0),
    }


def _get_day_changes(conn, date_str):
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            first_row.marketplace,
            first_row.account,
            first_row.sku,
            first_row.price AS first_price,
            max_prices.max_price AS max_price,
            min_prices.min_price AS min_price,
            last_row.price AS last_price,
            ((max_prices.max_price - first_row.price) / first_row.price) * 100.0 AS max_growth_pct,
            ((min_prices.min_price - first_row.price) / first_row.price) * 100.0 AS max_drop_pct,
            ((last_row.price - first_row.price) / first_row.price) * 100.0 AS final_change_pct
        FROM (
            SELECT ph.marketplace, ph.account, ph.sku, ph.price, ph.created_at
            FROM price_history ph
            INNER JOIN (
                SELECT marketplace, account, sku, MIN(created_at) AS first_ts
                FROM price_history
                WHERE date(created_at) = ?
                GROUP BY marketplace, account, sku
            ) t ON ph.marketplace = t.marketplace
               AND ph.account = t.account
               AND ph.sku = t.sku
               AND ph.created_at = t.first_ts
            WHERE date(ph.created_at) = ?
        ) first_row
        INNER JOIN (
            SELECT ph.marketplace, ph.account, ph.sku, ph.price, ph.created_at
            FROM price_history ph
            INNER JOIN (
                SELECT marketplace, account, sku, MAX(created_at) AS last_ts
                FROM price_history
                WHERE date(created_at) = ?
                GROUP BY marketplace, account, sku
            ) t ON ph.marketplace = t.marketplace
               AND ph.account = t.account
               AND ph.sku = t.sku
               AND ph.created_at = t.last_ts
            WHERE date(ph.created_at) = ?
        ) last_row
            ON first_row.marketplace = last_row.marketplace
           AND first_row.account = last_row.account
           AND first_row.sku = last_row.sku
        INNER JOIN (
            SELECT marketplace, account, sku, MAX(price) AS max_price
            FROM price_history
            WHERE date(created_at) = ?
            GROUP BY marketplace, account, sku
        ) max_prices
            ON first_row.marketplace = max_prices.marketplace
           AND first_row.account = max_prices.account
           AND first_row.sku = max_prices.sku
        INNER JOIN (
            SELECT marketplace, account, sku, MIN(price) AS min_price
            FROM price_history
            WHERE date(created_at) = ?
            GROUP BY marketplace, account, sku
        ) min_prices
            ON first_row.marketplace = min_prices.marketplace
           AND first_row.account = min_prices.account
           AND first_row.sku = min_prices.sku
        WHERE first_row.price IS NOT NULL
          AND max_prices.max_price IS NOT NULL
          AND min_prices.min_price IS NOT NULL
          AND last_row.price IS NOT NULL
          AND first_row.price > 0
        """,
        (date_str, date_str, date_str, date_str, date_str, date_str),
    )
    rows = cursor.fetchall()
    changes = []
    for row in rows:
        changes.append(
            {
                "marketplace": row[0],
                "account": row[1],
                "sku": row[2],
                "first_price": float(row[3]),
                "max_price": float(row[4]),
                "min_price": float(row[5]),
                "last_price": float(row[6]),
                "max_growth_pct": float(row[7]),
                "max_drop_pct": float(row[8]),
                "final_change_pct": float(row[9]),
            }
        )
    return changes


def _format_change_row(item, target_price_key, target_change_key):
    return (
        f"- {item['marketplace']} | {item['account']} | SKU {item['sku']}: "
        f"{item['first_price']:.2f} -> {item[target_price_key]:.2f} "
        f"({item[target_change_key]:+.2f}%)"
    )


def generate_daily_report_text(report_date=None):
    """
    Build daily text report from price_history for a given date (YYYY-MM-DD).
    If report_date is not provided, use today's date.
    """
    date_str = _normalize_report_date(report_date)
    conn = sqlite3.connect(DB_NAME)
    try:
        stats = _get_day_stats(conn, date_str)
        lines = [
            "Здравствуйте!",
            "",
            "Это ежедневный отчет системы Price Monitor.",
            f"Дата: {date_str}",
            "",
            "Краткая статистика:",
            f"- Всего записей: {stats['total_records']}",
            f"- Уникальных SKU: {stats['unique_skus']}",
            f"- Уникальных аккаунтов: {stats['unique_accounts']}",
            "",
        ]

        if stats["total_records"] == 0:
            lines.append("За выбранную дату данные отсутствуют.")
            lines.append("")
            lines.append("—")
            lines.append("Price Monitor")
            lines.append("Автоматическое уведомление")
            return "\n".join(lines)

        changes = _get_day_changes(conn, date_str)
        if not changes:
            lines.append("За выбранную дату данные отсутствуют.")
            lines.append("")
            lines.append("—")
            lines.append("Price Monitor")
            lines.append("Автоматическое уведомление")
            return "\n".join(lines)

        top_growth = sorted(changes, key=lambda x: x["max_growth_pct"], reverse=True)[:5]
        top_drop = sorted(changes, key=lambda x: x["max_drop_pct"])[:5]
        top_final_change = sorted(changes, key=lambda x: abs(x["final_change_pct"]), reverse=True)[:5]

        lines.append("Максимальный рост за день (топ-5):")
        for item in top_growth:
            lines.append(_format_change_row(item, "max_price", "max_growth_pct"))
        lines.append("")

        lines.append("Максимальное снижение за день (топ-5):")
        for item in top_drop:
            lines.append(_format_change_row(item, "min_price", "max_drop_pct"))
        lines.append("")

        lines.append("Итоговое изменение к концу дня (топ-5 по модулю):")
        for item in top_final_change:
            lines.append(_format_change_row(item, "last_price", "final_change_pct"))
        lines.append("")
        lines.append("—")
        lines.append("Price Monitor")
        lines.append("Автоматическое уведомление")

        return "\n".join(lines)
    finally:
        conn.close()
