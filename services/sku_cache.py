import json
import os
from datetime import datetime, timedelta


CACHE_FILE = "cache_sku.json"


def load_cache():

    if not os.path.exists(CACHE_FILE):
        return {}

    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_cache(data):

    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except OSError as e:
        print(f"Cache write failed: {e}")
        raise


def get_cached_sku(account):

    cache = load_cache()

    if account not in cache:
        return None

    entry = cache[account]
    if not isinstance(entry, dict) or "time" not in entry or "data" not in entry:
        return None

    try:
        timestamp = datetime.fromisoformat(entry["time"])
    except (TypeError, ValueError):
        return None

    if datetime.now() - timestamp > timedelta(hours=24):
        return None

    return entry["data"]


def save_sku(account, data):

    cache = load_cache()

    cache[account] = {
        "time": datetime.now().isoformat(),
        "data": data
    }

    save_cache(cache)