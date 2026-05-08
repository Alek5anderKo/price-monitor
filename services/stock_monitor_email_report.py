from services.account_display import get_account_display_name


def build_stock_monitor_email_text(problematic_rows, days_threshold):
    """
    Build business-style email grouped by marketplace/account.
    """
    lines = [
        "Здравствуйте!",
        "",
        "Направляем результаты ежедневной проверки остатков.",
        f"Расчетный порог: менее {days_threshold:.0f} дней.",
        "",
    ]

    grouped = {}
    for row in problematic_rows:
        key = (row["marketplace"], row["account"])
        grouped.setdefault(key, []).append(row)

    for (marketplace, account), rows in grouped.items():
        lines.append(f"Маркетплейс: {marketplace}")
        lines.append(f"Аккаунт: {get_account_display_name(account)}")
        for row in rows:
            lines.append(
                (
                    f"- SKU {row['sku']}, остаток: {row['current_stock']}, "
                    f"заказы 7/14/30: {row['orders_7']}/{row['orders_14']}/{row['orders_30']}, "
                    f"среднее 7/14/30: {row['avg_7']:.2f}/{row['avg_14']:.2f}/{row['avg_30']:.2f}, "
                    f"расчетная скорость: {row['avg_daily_orders']:.2f}, "
                    f"дней запаса: {row['days_left']:.2f}"
                )
            )
        lines.append("")

    lines.append("С уважением,")
    lines.append("MP Monitor")
    lines.append("Автоматическое уведомление")
    return "\n".join(lines)


def normalize_stock_monitor_recipients(raw_value):
    """
    Parse STOCK_MONITOR_EMAILS:
    - empty/None -> None (fallback to default recipients in email_notifier)
    - otherwise -> list of trimmed non-empty emails
    """
    if raw_value is None:
        return None
    text = str(raw_value).strip()
    if not text:
        return None
    recipients = [item.strip() for item in text.split(",")]
    recipients = [item for item in recipients if item]
    return recipients or None
