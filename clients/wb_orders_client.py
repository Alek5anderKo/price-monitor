"""
WB orders for Stock Monitor via Statistics API (not seller-analytics sales-funnel).

GET https://statistics-api.wildberries.ru/api/v1/supplier/orders
- One initial window: dateFrom = now - 30 days (MSK), flag=0.
- If response hits ~80k rows, WB requires follow-up requests with dateFrom = last row's
  lastChangeDate; we merge and still filter each line by order `date` into 7/14/30 days.
"""
import logging
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

WB_ORDERS_STATS_URL = "https://statistics-api.wildberries.ru/api/v1/supplier/orders"
API_TIMEOUT = 30
# At most one retry for non-429 failures; no retries on 429.
MAX_ATTEMPTS = 2
RETRY_DELAY_SECONDS = 2
WB_ROW_WARN_THRESHOLD = 78000
# WB Statistics timestamps are documented as Moscow time; use fixed UTC+3 (no tzdata dependency).
MSK_TZ = timezone(timedelta(hours=3), name="MSK")


def _wb_headers(api_key):
    return {"Authorization": api_key or ""}


def _extract_sku(row):
    """Match wb_stock_client: vendorCode first, then supplier article, then nmId."""
    if not isinstance(row, dict):
        return None
    for key in ("vendorCode", "supplierArticle"):
        val = row.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    nm_id = row.get("nmId") or row.get("nmID")
    if nm_id is not None:
        return str(nm_id)
    return None


def _parse_order_datetime(row):
    """
    Prefer `date` (order moment), then `lastChangeDate` (WB service update time).
    Naive strings without timezone are interpreted as UTC+3 / MSK per WB docs.
    """
    for key in ("date", "lastChangeDate"):
        raw = row.get(key)
        if raw is None:
            continue
        if isinstance(raw, datetime):
            dt = raw
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=MSK_TZ)
            return dt.astimezone(timezone.utc)
        if not isinstance(raw, str):
            continue
        s = raw.strip()
        if not s:
            continue
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=MSK_TZ)
        return dt.astimezone(timezone.utc)
    return None


def _row_counts_as_active_order(row):
    if not isinstance(row, dict):
        return False
    if row.get("isCancel") is True:
        return False
    return True


def _get_orders_page(url, headers, params):
    endpoint_path = urlparse(url).path
    for attempt in range(1, MAX_ATTEMPTS + 1):
        status_code = None
        try:
            response = requests.get(
                url, headers=headers, params=params, timeout=API_TIMEOUT
            )
            status_code = response.status_code
            if response.status_code == 200:
                try:
                    return response.json(), None
                except ValueError:
                    logger.warning(
                        "WB orders statistics: invalid JSON endpoint=%s",
                        endpoint_path,
                    )
                    return None, "format"
            if response.status_code == 429:
                logger.warning(
                    "WB orders statistics: rate limit endpoint=%s status=429",
                    endpoint_path,
                )
                return None, "429"
            if response.status_code in (401, 403):
                logger.warning(
                    "WB orders statistics: likely token/category issue endpoint=%s status=%s",
                    endpoint_path,
                    response.status_code,
                )
                return None, "auth"
            response_text_short = (response.text or "").strip().replace("\n", " ")[:500]
            logger.warning(
                "WB orders statistics: request failed endpoint=%s attempt=%s/%s status=%s response=%s",
                endpoint_path,
                attempt,
                MAX_ATTEMPTS,
                response.status_code,
                response_text_short,
            )
        except requests.RequestException as e:
            logger.warning(
                "WB orders statistics: request exception endpoint=%s attempt=%s/%s error=%s",
                endpoint_path,
                attempt,
                MAX_ATTEMPTS,
                e,
            )
        if attempt < MAX_ATTEMPTS and status_code != 429:
            time.sleep(RETRY_DELAY_SECONDS)
    return None, "failed"


def _aggregate_orders(rows, now_utc):
    """rows: list of dicts from Statistics orders API."""
    cutoff_7 = now_utc - timedelta(days=7)
    cutoff_14 = now_utc - timedelta(days=14)
    cutoff_30 = now_utc - timedelta(days=30)

    counts = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        if not _row_counts_as_active_order(row):
            continue
        sku = _extract_sku(row)
        if not sku:
            continue
        order_dt = _parse_order_datetime(row)
        if order_dt is None or order_dt < cutoff_30:
            continue

        if sku not in counts:
            counts[sku] = {"orders_7": 0, "orders_14": 0, "orders_30": 0}

        if order_dt >= cutoff_30:
            counts[sku]["orders_30"] += 1
        if order_dt >= cutoff_14:
            counts[sku]["orders_14"] += 1
        if order_dt >= cutoff_7:
            counts[sku]["orders_7"] += 1

    return {k: dict(v) for k, v in counts.items()}


def get_wb_orders(api_key):
    """
    WB orders via Statistics API GET /api/v1/supplier/orders (30-day pull, local 7/14/30).

    Returns: {"SKU": {"orders_7": int, "orders_14": int, "orders_30": int}}
    """
    if not api_key or not str(api_key).strip():
        logger.warning("WB stock monitor: missing API credentials")
        return {}

    now_utc = datetime.now(timezone.utc)
    start_msk = datetime.now(MSK_TZ) - timedelta(days=30)
    date_from_initial = start_msk.strftime("%Y-%m-%dT%H:%M:%S")

    headers = _wb_headers(api_key)
    all_rows = []
    date_from = date_from_initial
    pages = 0
    max_pages = 40

    while pages < max_pages:
        pages += 1
        params = {"dateFrom": date_from, "flag": 0}
        data, err = _get_orders_stats_page(headers, params)
        if err == "429":
            return {}
        if err in ("auth", "format"):
            return {}
        if err or data is None:
            logger.warning("WB orders statistics: giving up after failed request")
            return {}
        if not isinstance(data, list):
            logger.warning("WB orders statistics: unexpected response type (expected list)")
            return {}

        if len(data) >= WB_ROW_WARN_THRESHOLD:
            logger.warning(
                "WB orders statistics: large page (%s rows); WB may truncate without pagination",
                len(data),
            )

        all_rows.extend(data)

        if not data:
            break
        if len(data) < 80000:
            break

        last = data[-1]
        if not isinstance(last, dict):
            logger.warning("WB orders statistics: cannot paginate (bad last row)")
            break
        nxt = last.get("lastChangeDate")
        if not nxt or str(nxt).strip() == str(date_from).strip():
            break
        date_from = str(nxt).strip()

    result = _aggregate_orders(all_rows, now_utc)
    logger.info("WB order rows loaded=%s", len(result))
    return result


def _get_orders_stats_page(headers, params):
    """GET supplier/orders; returns (list|None, error_code|None)."""
    return _get_orders_page(WB_ORDERS_STATS_URL, headers, params)


def get_test_wb_orders(account_id):
    """Stub orders for 7/14/30 days for WB accounts."""
    if account_id != "wb_1":
        return {}
    return {
        "WB1-3001": {"orders_7": 14, "orders_14": 26, "orders_30": 55},
        "WB1-3002": {"orders_7": 9, "orders_14": 16, "orders_30": 34},
    }
