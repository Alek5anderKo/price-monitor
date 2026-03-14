import requests

OZON_PRODUCT_LIST = "https://api-seller.ozon.ru/v3/product/list"
OZON_PRICE_INFO = "https://api-seller.ozon.ru/v5/product/info/prices"


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

    response = requests.post(OZON_PRODUCT_LIST, json=payload, headers=headers)

    if response.status_code != 200:
        print("Ozon API error:", response.text)
        return []

    data = response.json()

    product_ids = []

    if "result" in data and "items" in data["result"]:
        items = data["result"]["items"]
    else:
        print("Unexpected product response:", data)
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
        "filter": {
            "product_id": product_ids
        },
        "limit": 1000
    }

    response = requests.post(OZON_PRICE_INFO, json=payload, headers=headers)

    if response.status_code != 200:
        print("Price API error:", response.text)
        return []

    data = response.json()

    prices = []

    if "result" in data and "items" in data["result"]:
        items = data["result"]["items"]
    elif "items" in data:
        items = data["items"]
    else:
        print("Unexpected price response:", data)
        return []

    for item in items:

        prices.append({
            "sku": item.get("offer_id"),
            "product_id": item.get("product_id"),
            "price": item.get("price", {}).get("price")
        })

    return prices