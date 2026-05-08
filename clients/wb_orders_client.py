import logging
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

WB_SALES_FUNNEL_URL = "https://seller-analytics-api.wildberries.ru/api/analytics/v3/sales-funnel/products"
API_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 2
RETRY_BACKOFF_429 = [20, 40, 60]
WINDOW_REQUEST_DELAY_SECONDS = 20


def _wb_headers(api_key):
    return {"Authorization": api_key or "", "Content-Type": "application/json"}


def _iso_date(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d")


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


def _iter_funnel_rows(data):
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    for key in ("data", "items", "rows", "report"):
        value = data.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            for subkey in ("items", "rows", "products"):
                subvalue = value.get(subkey)
                if isinstance(subvalue, list):
                    return subvalue
    return []


def _extract_sku(row):
    vendor_code = row.get("vendorCode")
    if vendor_code is not None and str(vendor_code).strip():
        return str(vendor_code).strip()
    nm_id = row.get("nmId") or row.get("nmID")
    if nm_id is not None:
        return str(nm_id)
    return None


def _extract_orders_count(row):
    statistic = row.get("statistic")
    if isinstance(statistic, dict):
        selected = statistic.get("selected")
        if isinstance(selected, dict):
            for nested_key in ("orderCount", "ordersCount"):
                if nested_key in selected:
                    try:
                        return max(0, int(selected.get(nested_key) or 0))
                    except (TypeError, ValueError):
                        return 0
    for key in ("ordersCount", "orders", "ordersCnt", "countOrders"):
        if key in row:
            try:
                return max(0, int(row.get(key) or 0))
            except (TypeError, ValueError):
                return 0
    return 0


def _load_orders_for_days(api_key, days):
    selected_end = datetime.now(timezone.utc)
    selected_start = selected_end - timedelta(days=max(1, int(days)) - 1)
    past_end = selected_start - timedelta(days=1)
    past_start = past_end - timedelta(days=max(1, int(days)) - 1)
    payload = {
        "selectedPeriod": {"start": _iso_date(selected_start), "end": _iso_date(selected_end)},
        "pastPeriod": {"start": _iso_date(past_start), "end": _iso_date(past_end)},
        "nmIds": [],
        "brandNames": [],
        "subjectIds": [],
        "tagIds": [],
        "skipDeletedNm": False,
        "orderBy": {"field": "openCard", "mode": "asc"},
        "limit": 1000,
        "offset": 0,
    }
    data = _post_json_with_retries(WB_SALES_FUNNEL_URL, _wb_headers(api_key), payload)
    if not isinstance(data, (dict, list)):
        return {}

    rows = _iter_funnel_rows(data)
    if not isinstance(rows, list):
        return {}

    result = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        sku = _extract_sku(row)
        if not sku:
            continue
        result[sku] = result.get(sku, 0) + _extract_orders_count(row)
    return result


def get_wb_orders(api_key):
    """
    Real WB orders via sales funnel analytics.
    Returns: {"SKU": {"orders_7": int, "orders_14": int, "orders_30": int}}
    """
    if not api_key or not str(api_key).strip():
        logger.warning("WB stock monitor: missing API credentials")
        return {}

    orders_7_map = _load_orders_for_days(api_key, 7)
    time.sleep(WINDOW_REQUEST_DELAY_SECONDS)
    orders_14_map = _load_orders_for_days(api_key, 14)
    time.sleep(WINDOW_REQUEST_DELAY_SECONDS)
    orders_30_map = _load_orders_for_days(api_key, 30)

    all_skus = set(orders_7_map) | set(orders_14_map) | set(orders_30_map)
    result = {}
    for sku in all_skus:
        result[sku] = {
            "orders_7": int(orders_7_map.get(sku, 0)),
            "orders_14": int(orders_14_map.get(sku, 0)),
            "orders_30": int(orders_30_map.get(sku, 0)),
        }
    logger.info("WB order rows loaded=%s", len(result))
    return result


def get_test_wb_orders(account_id):
    """Stub orders for 7/14/30 days for WB accounts."""
    if account_id != "wb_1":
        return {}
    return {
        "WB1-3001": {"orders_7": 14, "orders_14": 26, "orders_30": 55},
        "WB1-3002": {"orders_7": 9, "orders_14": 16, "orders_30": 34},
    }
