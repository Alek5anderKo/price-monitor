def get_test_ozon_stocks(account_id):
    """Stub stock data for Ozon accounts."""
    if account_id == "ozon_2":
        return [
            {"sku": "OZ2-1001", "product_id": 21001, "current_stock": 220},
            {"sku": "OZ2-1002", "product_id": 21002, "current_stock": 45},
        ]
    return [
        {"sku": "OZ1-1001", "product_id": 11001, "current_stock": 120},
        {"sku": "OZ1-1002", "product_id": 11002, "current_stock": 18},
    ]
