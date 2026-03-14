import json
import os
from dotenv import load_dotenv

MARKETPLACE_OZON = "ozon"
MARKETPLACE_WILDBERIES = "wildberries"

# Fallback env names for older .env format (OZON1_CLIENT_ID / OZON1_API_KEY etc.)
_OZON_ENV_FALLBACK = {
    "OZON_CLIENT_ID_1": "OZON1_CLIENT_ID",
    "OZON_API_KEY_1": "OZON1_API_KEY",
    "OZON_CLIENT_ID_2": "OZON2_CLIENT_ID",
    "OZON_API_KEY_2": "OZON2_API_KEY",
}


def _get_env_with_fallback(name):
    """Resolve env variable: try primary name, then fallback for known Ozon names."""
    v = os.getenv(name)
    if v is not None and str(v).strip():
        return v.strip()
    fallback = _OZON_ENV_FALLBACK.get(name)
    if fallback:
        v = os.getenv(fallback)
        if v is not None and str(v).strip():
            return v.strip()
    return None


def load_config():
    """Загружает список аккаунтов из config/accounts.json. name каждого аккаунта должен быть уникален."""
    load_dotenv(".env")

    try:
        with open("config/accounts.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError("config/accounts.json not found")
    except json.JSONDecodeError as e:
        raise ValueError(f"config/accounts.json invalid JSON: {e}") from e

    accounts_list = data.get("accounts", [])
    if not isinstance(accounts_list, list):
        return []

    accounts = []
    seen_names = set()

    for acc in accounts_list:
        if not isinstance(acc, dict):
            continue
        marketplace = acc.get("marketplace")
        name = acc.get("name")
        if not marketplace or not name:
            continue
        if name in seen_names:
            continue
        seen_names.add(name)

        account = {"marketplace": marketplace, "name": name}

        if marketplace == MARKETPLACE_OZON:
            client_id_env = acc.get("client_id_env")
            api_key_env = acc.get("api_key_env")
            if client_id_env is not None and api_key_env is not None:
                account["client_id_env"] = client_id_env
                account["api_key_env"] = api_key_env
                account["client_id"] = _get_env_with_fallback(client_id_env)
                account["api_key"] = _get_env_with_fallback(api_key_env)

        if marketplace == MARKETPLACE_WILDBERIES:
            api_key_env = acc.get("api_key_env")
            if api_key_env is not None:
                account["api_key"] = os.getenv(api_key_env)

        accounts.append(account)

    return accounts