import logging
import time
from urllib.parse import urlparse

import requests

from clients.wb_client import get_nm_to_article_map

logger = logging.getLogger(__name__)

WB_STOCKS_URL = "https://seller-analytics-api.wildberries.ru/api/analytics/v1/stocks-report/wb-warehouses"
API_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 2
RETRY_BACKOFF_429 = [20, 40, 60]


def _wb_headers(api_key):
    return {"Authorization": api_key or "", "Content-Type": "application/json"}


def _post_json_with_retries(url, headers, payload):
    endpoint_path = urlparse(url).path
    for attempt in range(1, MAX_RETRIES + 1):
        status_code = None
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=API_TIMEOUT)
            status_code = response.status_code
            if response.status_code == 200:
                return response.json()
            response_text_short = (response.text or "").strip().replace("\n", " ")[:500]
            hint = ""
            if response.status_code == 403:
                hint = " likely token permissions issue; check WB token categories and token type"
            elif response.status_code == 429:
                hint = " rate limit; retry delayed or skipped"
            elif response.status_code == 400:
                hint = " invalid request payload"
            elif response.status_code == 404:
                hint = " endpoint/base URL likely wrong"
            logger.warning(
                "WB request failed endpoint=%s attempt=%s/%s status=%s response=%s%s",
                endpoint_path,
                attempt,
                MAX_RETRIES,
                response.status_code,
                response_text_short,
                hint,
            )
        except requests.RequestException as e:
            logger.warning(
                "WB request exception endpoint=%s attempt=%s/%s error=%s",
                endpoint_path,
                attempt,
                MAX_RETRIES,
                e,
            )
        if attempt < MAX_RETRIES:
            if status_code == 429:
                time.sleep(RETRY_BACKOFF_429[min(attempt - 1, len(RETRY_BACKOFF_429) - 1)])
            else:
                time.sleep(RETRY_DELAY)
    return None


def _iter_stock_rows(data):
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    for key in ("data", "stocks", "items", "report"):
        value = data.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            for subkey in ("items", "stocks", "rows"):
                subvalue = value.get(subkey)
                if isinstance(subvalue, list):
                    return subvalue
    return []


def _log_sample_stock_row_keys(row):
    """Log field names from one stocks row (no token/headers/values)."""
    if not isinstance(row, dict) or not row:
        return
    logger.info("WB stocks sample row keys: %s", sorted(row.keys()))
    for field in ("vendorCode", "supplierArticle", "nmId", "nmID"):
        if field in row:
            logger.info("WB stocks sample has field: %s", field)


def _extract_vendor_article(row):
    """vendorCode / supplierArticle only (same priority as orders client)."""
    for key in ("vendorCode", "supplierArticle"):
        val = row.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return None


def _extract_nm_id(row):
    nm_id = row.get("nmId") or row.get("nmID")
    if nm_id is None:
        return None
    try:
        return int(nm_id)
    except (TypeError, ValueError):
        return None


def _extract_stock_value(row):
    # WB responses may use different field names by report type/version.
    for key in ("quantity", "stock", "stocks", "totalStock", "currentStock"):
        if key in row:
            try:
                return int(row.get(key) or 0)
            except (TypeError, ValueError):
                return 0
    return 0


def _merge_stock_bucket(bucket, sku, nm_id, stock_value):
    if sku not in bucket:
        bucket[sku] = {"sku": sku, "product_id": nm_id, "current_stock": 0}
    bucket[sku]["current_stock"] += stock_value
    if bucket[sku]["product_id"] is None and nm_id is not None:
        bucket[sku]["product_id"] = nm_id


def get_wb_stocks(api_key):
    """
    Real WB stocks (FBO), aggregated by vendor article SKU (GG001 / FF225 …).
    product_id is always nmId. Uses Content API cards map when stocks rows only have nmId.
    Returns: [{"sku": str, "product_id": nmId, "current_stock": int}, ...]
    """
    if not api_key or not str(api_key).strip():
        logger.warning("WB stock monitor: missing API credentials")
        return []

    data = _post_json_with_retries(WB_STOCKS_URL, _wb_headers(api_key), {})
    if not isinstance(data, (dict, list)):
        logger.warning("WB stock monitor: unexpected stocks response type")
        return []

    rows = _iter_stock_rows(data)
    if not isinstance(rows, list):
        logger.warning("WB stock monitor: unexpected stocks payload structure")
        return []

    aggregated = {}
    nm_id_buckets = {}
    sample_logged = False

    for row in rows:
        if not isinstance(row, dict):
            continue
        if not sample_logged:
            _log_sample_stock_row_keys(row)
            sample_logged = True

        nm_id = _extract_nm_id(row)
        stock_value = max(0, _extract_stock_value(row))
        if nm_id is None and stock_value <= 0:
            continue

        article = _extract_vendor_article(row)
        if article:
            _merge_stock_bucket(aggregated, article, nm_id, stock_value)
        elif nm_id is not None:
            _merge_stock_bucket(nm_id_buckets, str(nm_id), nm_id, stock_value)
        else:
            continue

    if nm_id_buckets:
        article_map = get_nm_to_article_map(api_key)
        mapped = 0
        unmapped = 0
        for nm_key, item in nm_id_buckets.items():
            article = article_map.get(nm_key)
            if article:
                mapped += 1
                _merge_stock_bucket(
                    aggregated,
                    article,
                    item.get("product_id"),
                    item["current_stock"],
                )
            else:
                unmapped += 1
        logger.info(
            "WB stock nmId->article applied: mapped=%s unmapped=%s (source=Content API cards/list)",
            mapped,
            unmapped,
        )

    result = list(aggregated.values())
    logger.info("WB stock rows loaded=%s", len(result))
    return result


def get_test_wb_stocks(account_id):
    """Stub stock data for WB accounts."""
    if account_id != "wb_1":
        return []
    return [
        {"sku": "WB1-3001", "product_id": 31001, "current_stock": 95},
        {"sku": "WB1-3002", "product_id": 31002, "current_stock": 12},
    ]
