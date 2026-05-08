import re


ACCOUNT_DISPLAY_NAME_MAP = {
    "ozon_1": "ozon_1 (Трейд)",
    "ozon_2": "ozon_2 (ИПЭ)",
    "wb_1": "wb_1 (Трейд)",
}


def _normalize_account_id(account_name):
    raw = str(account_name or "").strip().lower()
    raw = raw.replace("#", "_")
    raw = re.sub(r"[^a-z0-9]+", "_", raw)
    return raw.strip("_")


def get_account_display_name(account_name):
    account_id = _normalize_account_id(account_name)
    return ACCOUNT_DISPLAY_NAME_MAP.get(account_id, str(account_name))
