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

    for (marketplace, account), items in grouped.items():
        lines.append(f"Маркетплейс: {marketplace}")
        lines.append(f"Аккаунт: {get_account_display_name(account)}")
        lines.append("")
        for item in items:
            lines.append(f"- SKU {item.get('sku')}")
            lines.append("Продажи:")
            lines.append(f"- предыдущие 7 дней: {int(item.get('previous_7_orders') or 0)}")
            lines.append(f"- текущие 7 дней: {int(item.get('current_7_orders') or 0)}")
            lines.append(f"Изменение: {float(item.get('drop_percent') or 0.0):+.1f}%")
            lines.append(f"Текущий остаток: {int(item.get('current_stock') or 0)}")
            lines.append("")

    lines.append("С уважением,")
    lines.append("MP Monitor")
    lines.append("Автоматическое уведомление")
    return "\n".join(lines)
