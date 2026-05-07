import logging
import time
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

OZON_PRODUCT_LIST_URL = "https://api-seller.ozon.ru/v3/product/list"
OZON_PRODUCT_STOCKS_URL = "https://api-seller.ozon.ru/v4/product/info/stocks"
API_TIMEOUT = 20
MAX_RETRIES = 3
RETRY_DELAY = 2
PRODUCTS_LIMIT = 1000
STOCKS_CHUNK_SIZE = 1000


def _ozon_headers(client_id, api_key):
    return {
        "Client-Id": client_id,
        "Api-Key": api_key,
        "Content-Type": "application/json",
    }


def _post_json_with_retries(url, headers, payload):
    endpoint_path = urlparse(url).path
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=API_TIMEOUT)
            if response.status_code == 200:
                return response.json()
            response_text_short = (response.text or "").strip().replace("\n", " ")[:500]
            logger.warning(
                "Ozon request failed endpoint=%s attempt=%s/%s status=%s response=%s",
                endpoint_path,
                attempt,
                MAX_RETRIES,
                response.status_code,
                response_text_short,
            )
        except requests.RequestException as e:
            logger.warning(
                "Ozon request exception endpoint=%s attempt=%s/%s error=%s",
                endpoint_path,
                attempt,
                MAX_RETRIES,
                e,
            )
        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY)
    return None


def _load_ozon_products(client_id, api_key):
    headers = _ozon_headers(client_id, api_key)
    data = _post_json_with_retries(
        OZON_PRODUCT_LIST_URL,
        headers,
        {"filter": {}, "last_id": "", "limit": PRODUCTS_LIMIT},
    )
    if not isinstance(data, dict):
        return []
    items = data.get("result", {}).get("items", [])
    if not isinstance(items, list):
        return []
    products = []
    for item in items:
        if not isinstance(item, dict):
            continue
        product_id = item.get("product_id")
        offer_id = item.get("offer_id")
        if product_id is None or offer_id is None:
            continue
        products.append({"product_id": product_id, "offer_id": str(offer_id)})
    return products


def _extract_current_stock(stock_item):
    stocks = stock_item.get("stocks")
    if not isinstance(stocks, list):
        return 0
    total = 0
    for row in stocks:
        if not isinstance(row, dict):
            continue
        row_type = str(row.get("type") or "").strip().lower()
        if row_type and row_type != "fbo":
            continue
        present = row.get("present")
        try:
            total += int(present or 0)
        except (TypeError, ValueError):
            continue
    return max(0, total)


def get_ozon_stocks(client_id, api_key, return_meta=False):
    """
    Return real Ozon FBO stocks in format:
    {"sku": offer_id, "product_id": product_id, "current_stock": int}
    """
    if not client_id or not api_key:
        logger.warning("Ozon stock monitor: missing API credentials")
        empty = []
        meta = {"api_failed": True}
        return (empty, meta) if return_meta else empty

    products = _load_ozon_products(client_id, api_key)
    logger.info("Ozon stock monitor: SKU loaded=%s", len(products))
    if not products:
        empty = []
        meta = {"api_failed": True}
        return (empty, meta) if return_meta else empty

    headers = _ozon_headers(client_id, api_key)
    product_ids = [p["product_id"] for p in products]
    product_by_id = {p["product_id"]: p for p in products}
    result_rows = []
    api_failed = False

    for idx in range(0, len(product_ids), STOCKS_CHUNK_SIZE):
        chunk = product_ids[idx : idx + STOCKS_CHUNK_SIZE]
        if not chunk:
            continue
        limit = max(1, min(len(chunk), STOCKS_CHUNK_SIZE))
        data = _post_json_with_retries(
            OZON_PRODUCT_STOCKS_URL,
            headers,
            {"filter": {"product_id": chunk}, "limit": limit},
        )
        if not isinstance(data, dict):
            api_failed = True
            continue
        result = data.get("result")
        if isinstance(result, dict):
            items = result.get("items", [])
        elif isinstance(result, list):
            items = result
        else:
            items = data.get("items", [])
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            product_id = item.get("product_id")
            ref = product_by_id.get(product_id)
            if ref is None:
                continue
            result_rows.append(
                {
                    "sku": ref["offer_id"],
                    "product_id": product_id,
                    "current_stock": _extract_current_stock(item),
                }
            )

    logger.info("Ozon stock monitor: stock rows loaded=%s", len(result_rows))
    meta = {"api_failed": api_failed}
    return (result_rows, meta) if return_meta else result_rows


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
