def _should_trigger_stock_alert(
    current_stock,
    avg_daily_orders,
    days_left,
    min_avg_daily_orders,
    days_threshold,
):
    """Alert only when stock and velocity are positive and 0 < days_left < threshold."""
    if current_stock <= 0:
        return False
    if avg_daily_orders <= 0:
        return False
    if avg_daily_orders < min_avg_daily_orders:
        return False
    if days_left is None:
        return False
    if days_left <= 0:
        return False
    if days_left >= days_threshold:
        return False
    return True


def build_stock_monitor_rows(items, min_avg_daily_orders, days_threshold):
    """
    Compute stock monitor metrics and split result into:
    - rows_to_save: computed rows (skipped only when avg_daily_orders < min and > 0)
    - problematic_rows: rows matching alert rules (0 < days_left < threshold)
    """
    rows_to_save = []
    problematic_rows = []

    try:
        min_avg_daily_orders = float(min_avg_daily_orders)
    except (TypeError, ValueError):
        min_avg_daily_orders = 0.0
    try:
        days_threshold = float(days_threshold)
    except (TypeError, ValueError):
        days_threshold = 14.0

    for item in items:
        orders_7 = int(item.get("orders_7", 0) or 0)
        orders_14 = int(item.get("orders_14", 0) or 0)
        orders_30 = int(item.get("orders_30", 0) or 0)
        current_stock = int(item.get("current_stock", 0) or 0)

        avg_7 = orders_7 / 7.0
        avg_14 = orders_14 / 14.0
        avg_30 = orders_30 / 30.0
        avg_daily_orders = max(avg_7, avg_14, avg_30)

        if avg_daily_orders > 0 and avg_daily_orders < min_avg_daily_orders:
            continue

        if avg_daily_orders > 0:
            days_left = current_stock / avg_daily_orders
        else:
            days_left = None

        row = {
            "marketplace": item.get("marketplace"),
            "account": item.get("account"),
            "sku": str(item.get("sku")),
            "product_id": item.get("product_id"),
            "current_stock": current_stock,
            "orders_7": orders_7,
            "orders_14": orders_14,
            "orders_30": orders_30,
            "avg_7": avg_7,
            "avg_14": avg_14,
            "avg_30": avg_30,
            "avg_daily_orders": avg_daily_orders,
            "days_left": days_left,
            "alert_triggered": 0,
        }

        if _should_trigger_stock_alert(
            current_stock,
            avg_daily_orders,
            days_left,
            min_avg_daily_orders,
            days_threshold,
        ):
            row["alert_triggered"] = 1
            problematic_rows.append(row)

        rows_to_save.append(row)

    return rows_to_save, problematic_rows
