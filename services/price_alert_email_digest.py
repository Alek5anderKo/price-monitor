from datetime import datetime

from services.account_display import get_account_display_name


def price_alert_digest_subject(run_at=None):
    """Subject without prefix: Изменение цен за DD.MM.YYYY HH:MM"""
    run_at = run_at or datetime.now()
    stamp = run_at.strftime("%d.%m.%Y %H:%M")
    return f"Изменение цен за {stamp}"


def build_price_alert_digest_text(digest_items):
    """
    Plain-text digest grouped by marketplace + account.
    Each item: marketplace, account, display_sku, old_price, new_price, change, type.
    """
    lines = [
        "Здравствуйте!",
        "",
        "Обнаружены изменения цен.",
        "",
    ]
    if not digest_items:
        return "\n".join(lines)

    grouped = []
    current_key = None
    bucket = []
    for item in digest_items:
        key = (item["marketplace"], item["account"])
        if key != current_key:
            if bucket:
                grouped.append((current_key, bucket))
            current_key = key
            bucket = [item]
        else:
            bucket.append(item)
    if bucket:
        grouped.append((current_key, bucket))

    for (marketplace, account), items in grouped:
        lines.append(f"Маркетплейс: {marketplace}")
        lines.append(f"Аккаунт: {get_account_display_name(account)}")
        lines.append("")
        for row in items:
            change = float(row["change"])
            lines.append(
                f"- SKU {row['display_sku']} / {row['old_price']:.2f} -> {row['new_price']:.2f} "
                f"/ {change:+.1f}% / {row['type']}"
            )
        lines.append("")

    lines.extend(
        [
            "С уважением,",
            "MP Monitor",
            "Автоматическое уведомление",
        ]
    )
    return "\n".join(lines)
