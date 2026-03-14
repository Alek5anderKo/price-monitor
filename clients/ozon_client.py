import logging
import time

import requests

OZON_PRODUCT_LIST = "https://api-seller.ozon.ru/v3/product/list"
OZON_PRICE_INFO = "https://api-seller.ozon.ru/v5/product/info/prices"
API_TIMEOUT = 20
MAX_RETRIES = 3
RETRY_DELAY = 2


def get_products(client_id, api_key):

    headers = {
        "Client-Id": client_id,
        "Api-Key": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "filter": {},
        "last_id": "",
        "limit": 1000
    }

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                OZON_PRODUCT_LIST, json=payload, headers=headers, timeout=API_TIMEOUT
            )
            if response.status_code != 200:
                if attempt == MAX_RETRIES - 1:
                    raise RuntimeError("Ozon API error: %s" % (response.text,))
                logging.warning(
                    "API request failed, retrying (%s/%s)",
                    attempt + 1,
                    MAX_RETRIES,
                )
                time.sleep(RETRY_DELAY)
                continue
            data = response.json()
            break
        except requests.RequestException as e:
            if attempt == MAX_RETRIES - 1:
                raise
            logging.warning(
                "API request failed, retrying (%s/%s): %s",
                attempt + 1,
                MAX_RETRIES,
                e,
            )
            time.sleep(RETRY_DELAY)

    product_ids = []
    if "result" in data and "items" in data["result"]:
        items = data["result"]["items"]
    else:
        logging.warning("Unexpected product response: %s", data)
        return []

    for item in items:
        product_ids.append(item.get("product_id"))
    return product_ids


def get_prices(client_id, api_key, product_ids):

    headers = {
        "Client-Id": client_id,
        "Api-Key": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "filter": {"product_id": product_ids},
        "limit": 1000
    }

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                OZON_PRICE_INFO, json=payload, headers=headers, timeout=API_TIMEOUT
            )
            if response.status_code != 200:
                if attempt == MAX_RETRIES - 1:
                    raise RuntimeError("Price API error: %s" % (response.text,))
                logging.warning(
                    "API request failed, retrying (%s/%s)",
                    attempt + 1,
                    MAX_RETRIES,
                )
                time.sleep(RETRY_DELAY)
                continue
            data = response.json()
            break
        except requests.RequestException as e:
            if attempt == MAX_RETRIES - 1:
                raise
            logging.warning(
                "API request failed, retrying (%s/%s): %s",
                attempt + 1,
                MAX_RETRIES,
                e,
            )
            time.sleep(RETRY_DELAY)

    prices = []
    if "result" in data and "items" in data["result"]:
        items = data["result"]["items"]
    elif "items" in data:
        items = data["items"]
    else:
        logging.warning("Unexpected price response: %s", data)
        return []

    for item in items:
        prices.append({
            "sku": item.get("offer_id"),
            "product_id": item.get("product_id"),
            "price": item.get("price", {}).get("price")
        })
    return prices