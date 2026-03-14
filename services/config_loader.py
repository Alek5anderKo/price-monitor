import json
import os
from dotenv import load_dotenv


def load_config():

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

    for acc in accounts_list:
        if not isinstance(acc, dict):
            continue
        marketplace = acc.get("marketplace")
        name = acc.get("name")
        if not marketplace or not name:
            continue

        account = {"marketplace": marketplace, "name": name}

        if marketplace == "ozon":
            client_id_env = acc.get("client_id_env")
            api_key_env = acc.get("api_key_env")
            if client_id_env is not None and api_key_env is not None:
                account["client_id"] = os.getenv(client_id_env)
                account["api_key"] = os.getenv(api_key_env)

        if marketplace == "wildberries":
            api_key_env = acc.get("api_key_env")
            if api_key_env is not None:
                account["api_key"] = os.getenv(api_key_env)

        accounts.append(account)

    return accounts