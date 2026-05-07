def get_test_wb_orders(account_id):
    """Stub orders for 7/14/30 days for WB accounts."""
    if account_id != "wb_1":
        return {}
    return {
        "WB1-3001": {"orders_7": 14, "orders_14": 26, "orders_30": 55},
        "WB1-3002": {"orders_7": 9, "orders_14": 16, "orders_30": 34},
    }
