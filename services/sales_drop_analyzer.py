def detect_sales_drop_alerts(rows, strong_drop_factor, min_prev_orders, stopped_min_prev_orders):
    """
    Input row format:
    {
      "marketplace": "ozon",
      "account": "ozon_1",
      "sku": "...",
      "product_id": ...,
      "current_stock": int,
      "current_7_orders": int,
      "previous_7_orders": int
    }
    """
    alerts = []
    if not rows:
        return alerts

    try:
        strong_drop_factor = float(strong_drop_factor)
    except (TypeError, ValueError):
        strong_drop_factor = 3.0
    if strong_drop_factor <= 0:
        strong_drop_factor = 3.0

    try:
        min_prev_orders = int(min_prev_orders)
    except (TypeError, ValueError):
        min_prev_orders = 10
    try:
        stopped_min_prev_orders = int(stopped_min_prev_orders)
    except (TypeError, ValueError):
        stopped_min_prev_orders = 5

    for row in rows:
        try:
            current_stock = int(row.get("current_stock", 0) or 0)
            current_7 = int(row.get("current_7_orders", 0) or 0)
            previous_7 = int(row.get("previous_7_orders", 0) or 0)
        except (TypeError, ValueError):
            continue

        if current_stock <= 0:
            continue

        alert_type = None
        if previous_7 >= min_prev_orders and current_7 <= (previous_7 / strong_drop_factor):
            alert_type = "strong_drop"
        if previous_7 >= stopped_min_prev_orders and current_7 == 0:
            alert_type = "stopped_sales"
        if not alert_type:
            continue

        if previous_7 > 0:
            drop_percent = ((current_7 - previous_7) / previous_7) * 100.0
        else:
            drop_percent = 0.0

        alerts.append(
            {
                "marketplace": row.get("marketplace"),
                "account": row.get("account"),
                "sku": row.get("sku"),
                "product_id": row.get("product_id"),
                "current_stock": current_stock,
                "current_7_orders": current_7,
                "previous_7_orders": previous_7,
                "drop_percent": float(drop_percent),
                "type": alert_type,
            }
        )

    return alerts
