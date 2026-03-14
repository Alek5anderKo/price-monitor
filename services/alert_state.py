"""Состояние последнего алерта: cooldown по (marketplace, account, sku), чтобы не слать повтор при той же цене."""
import json
import logging
import os
from datetime import datetime, timedelta

from dotenv import load_dotenv

load_dotenv()

STATE_FILE = "alert_state.json"
KEY_SEP = "|"


def _int_env(name, default):
    """Read int from env; on missing or invalid value return default."""
    try:
        v = os.getenv(name)
        if v is None or str(v).strip() == "":
            return default
        return int(v)
    except (TypeError, ValueError):
        return default


ALERT_COOLDOWN_MINUTES = _int_env("ALERT_COOLDOWN_MINUTES", 60)


def _state_key(marketplace, account, sku):
    """Составной ключ: один и тот же SKU в разных аккаунтах имеет отдельный cooldown."""
    return f"{marketplace}{KEY_SEP}{account}{KEY_SEP}{sku}"


def load_state():
    """Загружает состояние из JSON. При ошибке или отсутствии файла возвращает {}."""
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(data):
    """Сохраняет состояние в JSON. При ошибке записи логирует и не прерывает выполнение."""
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError as e:
        logging.getLogger(__name__).error("Alert state file write failed: %s", e)


def should_send_alert(marketplace, account, sku, current_price):
    """
    Возвращает True, если алерт нужно отправить.
    Cooldown изолирован по (marketplace, account, sku).
    """
    state = load_state()
    key = _state_key(marketplace, account, sku)
    if key not in state:
        return True
    entry = state[key]
    if not isinstance(entry, dict) or "last_price" not in entry or "timestamp" not in entry:
        return True
    last_price = entry["last_price"]
    try:
        last_price = float(last_price)
        current_price = float(current_price)
    except (TypeError, ValueError):
        return True
    if last_price != current_price:
        return True
    try:
        ts = datetime.fromisoformat(entry["timestamp"])
    except (TypeError, ValueError):
        return True
    if datetime.now() - ts < timedelta(minutes=ALERT_COOLDOWN_MINUTES):
        return False
    return True


def update_alert_state(marketplace, account, sku, current_price):
    """Обновляет состояние после отправки алерта (по составному ключу)."""
    state = load_state()
    state[_state_key(marketplace, account, sku)] = {
        "last_price": current_price,
        "timestamp": datetime.now().isoformat(),
    }
    save_state(state)
