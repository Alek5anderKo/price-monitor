def get_test_wb_stocks(account_id):
    """Stub stock data for WB accounts."""
    if account_id != "wb_1":
        return []
    return [
        {"sku": "WB1-3001", "product_id": 31001, "current_stock": 95},
        {"sku": "WB1-3002", "product_id": 31002, "current_stock": 12},
    ]
