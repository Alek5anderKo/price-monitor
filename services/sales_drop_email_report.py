from services.account_display import get_account_display_name


def build_sales_drop_email_text(alerts):
    lines = [
        "Здравствуйте!",
        "",
        "По результатам еженедельной проверки обнаружены товары со снижением продаж.",
        "",
    ]

    grouped = {}
    for alert in alerts:
        key = (alert.get("marketplace"), alert.get("account"))
        grouped.setdefault(key, []).append(alert)

    first_block = True
    for (marketplace, account), items in grouped.items():
        if not first_block:
            lines.append("")
        first_block = False
        lines.append(f"Маркетплейс: {marketplace}")
        lines.append(f"Аккаунт: {get_account_display_name(account)}")
        lines.append("")
        for item in items:
            sku = item.get("sku")
            prev = int(item.get("previous_7_orders") or 0)
            curr = int(item.get("current_7_orders") or 0)
            drop = float(item.get("drop_percent") or 0.0)
            stock = int(item.get("current_stock") or 0)
            lines.append(
                f"- SKU {sku} / предыдущие 7 дней: {prev} / текущие 7 дней: {curr} / "
                f"изменение: {drop:+.1f}% / остаток: {stock}"
            )

    lines.append("")
    lines.append("С уважением,")
    lines.append("MP Monitor")
    lines.append("Автоматическое уведомление")
    return "\n".join(lines)
