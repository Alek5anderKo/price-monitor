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
            last_row.price AS last_price,
            ((last_row.price - first_row.price) / first_row.price) * 100.0 AS change_pct
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
        WHERE first_row.price IS NOT NULL
          AND last_row.price IS NOT NULL
          AND first_row.price > 0
        """,
        (date_str, date_str, date_str, date_str),
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
                "last_price": float(row[4]),
                "change_pct": float(row[5]),
            }
        )
    return changes


def _format_change_row(item):
    return (
        f"- {item['marketplace']} | {item['account']} | SKU {item['sku']}: "
        f"{item['first_price']:.2f} -> {item['last_price']:.2f} "
        f"({item['change_pct']:+.2f}%)"
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

        top_up = sorted(changes, key=lambda x: x["change_pct"], reverse=True)[:5]
        top_down = sorted(changes, key=lambda x: x["change_pct"])[:5]

        lines.append("Рост цен (топ-5):")
        for item in top_up:
            lines.append(_format_change_row(item))
        lines.append("")

        lines.append("Снижение цен (топ-5):")
        for item in top_down:
            lines.append(_format_change_row(item))
        lines.append("")
        lines.append("—")
        lines.append("Price Monitor")
        lines.append("Автоматическое уведомление")

        return "\n".join(lines)
    finally:
        conn.close()
