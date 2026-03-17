"""
Wildberries API client. One token with Promotion + Prices and Discounts scopes.
- cards/list (Content API): Promotion scope. Official request body with sort, cursor, filter. Paginated (limit 100 per page).
- list/goods/filter (Prices API): Prices and Discounts scope. Request body: nmList[]. Response: data.listGoods[], price from sizes[0]. Chunked when nmList > 1000.
Return format matches Ozon; sku is normalized to string for consistent dict lookups (SQLite keys are str).
"""
import logging
import time

import requests

logger = logging.getLogger(__name__)

CONTENT_CARDS_URL = "https://content-api.wildberries.ru/content/v2/get/cards/list"
PRICES_FILTER_URL = "https://discounts-prices-api.wildberries.ru/api/v2/list/goods/filter"
API_TIMEOUT = 10
MAX_RETRIES = 3
RETRY_DELAY = 2
CARDS_PAGE_LIMIT = 100
PRICES_NMLIST_CHUNK = 1000

# Official request body for cards/list (Promotion scope)
CARDS_LIST_PAYLOAD = {
    "settings": {
        "sort": {"ascending": True},
        "cursor": {"limit": CARDS_PAGE_LIMIT},
        "filter": {"withPhoto": -1},
    }
}


def _build_cards_payload(cursor_updated_at=None, cursor_nm_id=None):
    """Build request body for cards/list. First page: no cursor.updatedAt/nmID; next pages: include both."""
    payload = {
        "settings": {
            "sort": {"ascending": True},
            "cursor": {"limit": CARDS_PAGE_LIMIT},
            "filter": {"withPhoto": -1},
        }
    }
    if cursor_updated_at is not None and cursor_nm_id is not None:
        payload["settings"]["cursor"]["updatedAt"] = cursor_updated_at
        payload["settings"]["cursor"]["nmID"] = cursor_nm_id
    return payload


def get_products(api_key):
    """
    Fetch product cards from WB Content API (Promotion scope). Paginated: requests until response returns < limit.
    Returns list of {"sku": str(nmID), "product_id": nmID}. Deduplicated by str(nmID).
    Response: { "cards": [ { "nmID": ... }, ... ], "cursor": { "updatedAt", "nmID" } }
    """
    headers = {"Authorization": api_key or ""}
    all_products = {}  # str(nmID) -> item, dedupe across pages
    page = 1
    cursor_updated_at = None
    cursor_nm_id = None

    while True:
        payload = _build_cards_payload(cursor_updated_at, cursor_nm_id)
        data = None
        for attempt in range(MAX_RETRIES):
            try:
                resp = requests.post(
                    CONTENT_CARDS_URL,
                    json=payload,
                    headers=headers,
                    timeout=API_TIMEOUT,
                )
                if resp.status_code != 200:
                    if attempt == MAX_RETRIES - 1:
                        raise RuntimeError("WB Content API error: %s" % (resp.text,))
                    logger.warning(
                        "WB API request failed, retrying (%s/%s): %s",
                        attempt + 1,
                        MAX_RETRIES,
                        resp.text[:200] if resp.text else resp.status_code,
                    )
                    time.sleep(RETRY_DELAY)
                    continue
                data = resp.json()
                break
            except requests.RequestException as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                logger.warning(
                    "WB API request failed, retrying (%s/%s): %s",
                    attempt + 1,
                    MAX_RETRIES,
                    e,
                )
                time.sleep(RETRY_DELAY)

        cards = data.get("cards") if isinstance(data, dict) else None
        if not isinstance(cards, list):
            logger.warning("Unexpected WB cards response: %s", data)
            break

        for card in cards:
            if not isinstance(card, dict):
                continue
            nm_id = card.get("nmID")
            if nm_id is None:
                continue
            key = str(nm_id)
            all_products[key] = {"sku": key, "product_id": nm_id}

        logger.info(
            "WB cards page %d loaded: %d (total collected: %d)",
            page,
            len(cards),
            len(all_products),
        )

        if len(cards) < CARDS_PAGE_LIMIT:
            break

        cursor = data.get("cursor") if isinstance(data, dict) else {}
        cursor_updated_at = cursor.get("updatedAt")
        cursor_nm_id = cursor.get("nmID")
        if cursor_updated_at is None or cursor_nm_id is None:
            break
        page += 1

    return list(all_products.values())


def _extract_list_goods(data):
    """Extract listGoods from WB prices API response. Returns list or None."""
    if not isinstance(data, dict):
        return None
    list_goods = data.get("listGoods")
    if list_goods is None and "data" in data:
        list_goods = data.get("data", {}).get("listGoods") if isinstance(data.get("data"), dict) else None
    return list_goods if isinstance(list_goods, list) else None


def _parse_list_goods(list_goods):
    """Parse listGoods into list of {sku, product_id, price}. Shared by single and chunked requests."""
    if not isinstance(list_goods, list):
        return []
    result = []
    for row in list_goods:
        if not isinstance(row, dict):
            continue
        nm_id = row.get("nmID")
        sizes = row.get("sizes")
        if not isinstance(sizes, list) or not sizes:
            continue
        first_size = sizes[0] if isinstance(sizes[0], dict) else None
        if not first_size:
            continue
        price = first_size.get("discountedPrice")
        if price is None:
            price = first_size.get("price")
        if nm_id is None or price is None:
            continue
        try:
            price = float(price)
        except (TypeError, ValueError):
            continue
        result.append({"sku": str(nm_id), "product_id": nm_id, "price": price})
    return result


def _request_prices_one_chunk(api_key, nm_ids_chunk):
    """POST one nmList chunk; returns list_goods or None on failure."""
    headers = {"Authorization": api_key or ""}
    payload = {"nmList": nm_ids_chunk}
    data = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(
                PRICES_FILTER_URL,
                json=payload,
                headers=headers,
                timeout=API_TIMEOUT,
            )
            if resp.status_code != 200:
                if attempt == MAX_RETRIES - 1:
                    raise RuntimeError("WB Prices API error: %s" % (resp.text,))
                logger.warning(
                    "WB Prices API request failed, retrying (%s/%s): %s",
                    attempt + 1,
                    MAX_RETRIES,
                    resp.text[:200] if resp.text else resp.status_code,
                )
                time.sleep(RETRY_DELAY)
                continue
            data = resp.json()
            break
        except requests.RequestException as e:
            if attempt == MAX_RETRIES - 1:
                raise
            logger.warning(
                "WB Prices API request failed, retrying (%s/%s): %s",
                attempt + 1,
                MAX_RETRIES,
                e,
            )
            time.sleep(RETRY_DELAY)
    return _extract_list_goods(data)


def get_prices(api_key, products):
    """
    Fetch prices from WB Prices API (Prices and Discounts scope). products: [{"sku": nmID, "product_id": nmID}, ...].
    Request body: {"nmList": [...]}. When products > 1000, nmList is chunked (max 1000 per request); results merged.
    Response: data.listGoods[]; each item nmID + sizes[]; price = sizes[0].discountedPrice or sizes[0].price.
    Returns list of {"sku": str(nmID), "product_id": nmID, "price": price}.
    """
    if not products:
        return []

    nm_ids = []
    for p in products:
        if isinstance(p, dict):
            pid = p.get("product_id") or p.get("sku")
            if pid is not None:
                nm_ids.append(pid)
        elif p is not None:
            nm_ids.append(p)

    if not nm_ids:
        return []

    if len(nm_ids) > PRICES_NMLIST_CHUNK:
        # Official nmList max size 1000; request chunk by chunk and merge
        merged_list_goods = []
        for i in range(0, len(nm_ids), PRICES_NMLIST_CHUNK):
            chunk = nm_ids[i : i + PRICES_NMLIST_CHUNK]
            list_goods = _request_prices_one_chunk(api_key, chunk)
            if list_goods:
                merged_list_goods.extend(list_goods)
        return _parse_list_goods(merged_list_goods)

    # Single request when nmList <= 1000
    list_goods = _request_prices_one_chunk(api_key, nm_ids)
    if list_goods is None:
        logger.warning("Unexpected WB prices response")
        return []
    return _parse_list_goods(list_goods)
