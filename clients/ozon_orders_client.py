def get_test_ozon_orders(account_id):
    """Stub orders for 7/14/30 days for Ozon accounts."""
    if account_id == "ozon_2":
        return {
            "OZ2-1001": {"orders_7": 42, "orders_14": 79, "orders_30": 160},
            "OZ2-1002": {"orders_7": 21, "orders_14": 42, "orders_30": 88},
        }
    return {
        "OZ1-1001": {"orders_7": 35, "orders_14": 70, "orders_30": 150},
        "OZ1-1002": {"orders_7": 10, "orders_14": 19, "orders_30": 45},
    }
