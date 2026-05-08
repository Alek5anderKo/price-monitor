import logging
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

OZON_FBO_POSTINGS_URL = "https://api-seller.ozon.ru/v2/posting/fbo/list"
API_TIMEOUT = 20
MAX_RETRIES = 3
RETRY_DELAY = 2
POSTINGS_LIMIT = 1000


def _ozon_headers(client_id, api_key):
    return {
        "Client-Id": client_id,
        "Api-Key": api_key,
        "Content-Type": "application/json",
    }


def _iso_utc(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


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


def _count_orders_for_days(client_id, api_key, days):
    headers = _ozon_headers(client_id, api_key)
    since_dt = datetime.now(timezone.utc) - timedelta(days=days)
    return _count_orders_for_period(client_id, api_key, since_dt, datetime.now(timezone.utc))


def _count_orders_for_period(client_id, api_key, since_dt, to_dt):
    headers = _ozon_headers(client_id, api_key)
    payload = {
        "dir": "ASC",
        "filter": {
            "since": _iso_utc(since_dt),
            "to": _iso_utc(to_dt),
        },
        "limit": POSTINGS_LIMIT,
        "offset": 0,
    }
    counts = {}

    while True:
        data = _post_json_with_retries(OZON_FBO_POSTINGS_URL, headers, payload)
        if not isinstance(data, dict):
            return {}
        result = data.get("result")
        if isinstance(result, dict):
            postings = result.get("postings", [])
        else:
            postings = result if isinstance(result, list) else []
        if not isinstance(postings, list):
            return {}
        for posting in postings:
            if not isinstance(posting, dict):
                continue
            products = posting.get("products", [])
            if not isinstance(products, list):
                continue
            for product in products:
                if not isinstance(product, dict):
                    continue
                sku = product.get("offer_id")
                if sku is None:
                    continue
                qty = product.get("quantity", 1)
                try:
                    qty = int(qty)
                except (TypeError, ValueError):
                    qty = 1
                key = str(sku)
                counts[key] = counts.get(key, 0) + max(0, qty)

        if len(postings) < POSTINGS_LIMIT:
            break
        payload["offset"] += POSTINGS_LIMIT

    return counts


def get_ozon_orders(client_id, api_key):
    """
    Return dict by sku with orders for 7/14/30 days:
    {"sku": {"orders_7": int, "orders_14": int, "orders_30": int}}
    """
    if not client_id or not api_key:
        logger.warning("Ozon stock monitor: missing API credentials")
        return {}

    counts_7 = _count_orders_for_days(client_id, api_key, 7)
    counts_14 = _count_orders_for_days(client_id, api_key, 14)
    counts_30 = _count_orders_for_days(client_id, api_key, 30)

    all_skus = set(counts_7.keys()) | set(counts_14.keys()) | set(counts_30.keys())
    result = {}
    for sku in all_skus:
        result[sku] = {
            "orders_7": int(counts_7.get(sku, 0)),
            "orders_14": int(counts_14.get(sku, 0)),
            "orders_30": int(counts_30.get(sku, 0)),
        }

    logger.info("Ozon stock monitor: order rows loaded=%s", len(result))
    return result


def get_ozon_orders_for_period(client_id, api_key, date_from, date_to):
    """
    Return dict sku -> orders count for a custom UTC period [date_from, date_to].
    date_from/date_to can be datetime or ISO-like string accepted by datetime.fromisoformat.
    """
    if not client_id or not api_key:
        logger.warning("Ozon stock monitor: missing API credentials")
        return {}
    try:
        if isinstance(date_from, datetime):
            from_dt = date_from
        else:
            from_dt = datetime.fromisoformat(str(date_from))
        if isinstance(date_to, datetime):
            to_dt = date_to
        else:
            to_dt = datetime.fromisoformat(str(date_to))
        if from_dt.tzinfo is None:
            from_dt = from_dt.replace(tzinfo=timezone.utc)
        if to_dt.tzinfo is None:
            to_dt = to_dt.replace(tzinfo=timezone.utc)
        if from_dt > to_dt:
            return {}
    except (TypeError, ValueError):
        return {}
    return _count_orders_for_period(client_id, api_key, from_dt, to_dt)


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
