def build_stock_monitor_rows(items, min_avg_daily_orders, days_threshold):
    """
    Compute stock monitor metrics and split result into:
    - rows_to_save: all computed rows that passed avg_daily filter
    - problematic_rows: rows with days_left < days_threshold
    """
    rows_to_save = []
    problematic_rows = []

    for item in items:
        orders_7 = int(item.get("orders_7", 0) or 0)
        orders_14 = int(item.get("orders_14", 0) or 0)
        orders_30 = int(item.get("orders_30", 0) or 0)
        current_stock = int(item.get("current_stock", 0) or 0)

        avg_7 = orders_7 / 7.0
        avg_14 = orders_14 / 14.0
        avg_30 = orders_30 / 30.0
        avg_daily_orders = max(avg_7, avg_14, avg_30)

        if avg_daily_orders < min_avg_daily_orders:
            continue

        days_left = current_stock / avg_daily_orders if avg_daily_orders > 0 else 0.0
        alert_triggered = 1 if days_left < days_threshold else 0

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
            "alert_triggered": alert_triggered,
        }

        rows_to_save.append(row)
        if alert_triggered:
            problematic_rows.append(row)

    return rows_to_save, problematic_rows
