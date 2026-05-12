"""
Временная проверка: топ-10 SKU по orders_30 из get_wb_orders (Statistics API).
Не логирует и не печатает токен. Удалите файл после проверки, если не хотите хранить в репозитории.

Запуск из корня проекта:
  python snippets/check_wb_orders_top.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    import os

    os.chdir(ROOT)

    from dotenv import load_dotenv

    from clients.wb_orders_client import get_wb_orders
    from services.config_loader import load_config

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    load_dotenv(ROOT / ".env")

    api_key = None
    for acc in load_config():
        if acc.get("marketplace") == "wildberries":
            api_key = acc.get("api_key")
            break

    if not api_key or not str(api_key).strip():
        print("Нет WB api_key: проверьте config/accounts.json и .env", file=sys.stderr)
        sys.exit(1)

    orders = get_wb_orders(api_key)
    rows = [
        (
            sku,
            int(v.get("orders_7", 0) or 0),
            int(v.get("orders_14", 0) or 0),
            int(v.get("orders_30", 0) or 0),
        )
        for sku, v in orders.items()
    ]
    rows.sort(key=lambda x: -x[3])

    print("sku\torders_7\torders_14\torders_30")
    for sku, o7, o14, o30 in rows[:10]:
        print(f"{sku}\t{o7}\t{o14}\t{o30}")


if __name__ == "__main__":
    main()
