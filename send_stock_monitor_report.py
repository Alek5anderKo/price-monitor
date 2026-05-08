import logging
import os
import re
from datetime import datetime

from dotenv import load_dotenv

from clients.ozon_orders_client import get_ozon_orders, get_test_ozon_orders
from clients.ozon_stock_client import get_ozon_stocks, get_test_ozon_stocks
from clients.wb_orders_client import get_test_wb_orders, get_wb_orders
from clients.wb_stock_client import get_test_wb_stocks, get_wb_stocks
from database.db import init_db, save_stock_monitor_rows
from services.config_loader import load_config
from services.email_notifier import send_email
from services.stock_monitor_analyzer import build_stock_monitor_rows
from services.stock_monitor_email_report import (
    build_stock_monitor_email_text,
    normalize_stock_monitor_recipients,
)

ALLOWED_ACCOUNT_IDS = {"ozon_1", "ozon_2", "wb_1"}
DEFAULT_DAYS_THRESHOLD = 14.0
DEFAULT_MIN_AVG_DAILY_ORDERS = 0.0


def _setup_logging():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def _bool_env(name, default=False):
    v = os.getenv(name)
    if v is None:
        return default
    normalized = str(v).strip().lower()
    if normalized in ("true", "1", "yes"):
        return True
    if normalized in ("false", "0", "no", ""):
        return False
    return default


def _float_env(name, default):
    try:
        v = os.getenv(name)
        if v is None or str(v).strip() == "":
            return float(default)
        return float(v)
    except (TypeError, ValueError):
        return float(default)


def _normalize_account_id(name):
    raw = str(name or "").strip().lower()
    raw = raw.replace("#", "_")
    raw = re.sub(r"[^a-z0-9]+", "_", raw)
    return raw.strip("_")


def _get_data_for_account(
    account_id, marketplace, client_id=None, api_key=None, wb_enabled=False
):
    if marketplace == "ozon" and account_id in {"ozon_1", "ozon_2"}:
        stocks, stock_meta = get_ozon_stocks(client_id, api_key, return_meta=True)
        orders = get_ozon_orders(client_id, api_key)
        if not stocks:
            if stock_meta.get("api_failed"):
                logging.warning("Ozon real stock API failed; using test fallback")
            else:
                logging.warning("Ozon real stock API failed; stock rows empty")
            stocks = get_test_ozon_stocks(account_id)
        if not orders:
            logging.warning("Ozon API unavailable or empty for %s; using test orders fallback", account_id)
            orders = get_test_ozon_orders(account_id)
        return stocks, orders
    if marketplace == "wildberries" and account_id == "wb_1":
        if not wb_enabled:
            logging.info("WB Stock Monitor is disabled by STOCK_MONITOR_WB_ENABLED")
            return [], {}
        stocks = get_wb_stocks(api_key)
        orders = get_wb_orders(api_key)
        logging.info("WB stock rows loaded=%s", len(stocks))
        logging.info("WB order rows loaded=%s", len(orders))
        if not stocks or not orders:
            logging.warning("WB real API failed; using test fallback")
            if not stocks:
                stocks = get_test_wb_stocks(account_id)
            if not orders:
                orders = get_test_wb_orders(account_id)
        return stocks, orders
    return [], {}


def _combine_stock_and_orders(marketplace, account_name, stocks, orders_map):
    combined = []
    for stock_item in stocks:
        sku = str(stock_item.get("sku"))
        order_item = orders_map.get(sku, {})
        combined.append(
            {
                "marketplace": marketplace,
                "account": account_name,
                "sku": sku,
                "product_id": stock_item.get("product_id"),
                "current_stock": int(stock_item.get("current_stock", 0) or 0),
                "orders_7": int(order_item.get("orders_7", 0) or 0),
                "orders_14": int(order_item.get("orders_14", 0) or 0),
                "orders_30": int(order_item.get("orders_30", 0) or 0),
            }
        )
    return combined


def _to_db_tuple(row):
    return (
        row["marketplace"],
        row["account"],
        row["sku"],
        row["product_id"],
        row["current_stock"],
        row["orders_7"],
        row["orders_14"],
        row["orders_30"],
        row["avg_7"],
        row["avg_14"],
        row["avg_30"],
        row["avg_daily_orders"],
        row["days_left"],
        row["alert_triggered"],
    )


def main():
    load_dotenv()
    _setup_logging()

    if not _bool_env("STOCK_MONITOR_ENABLED", False):
        logging.info(
            "Stock Monitor is disabled by STOCK_MONITOR_ENABLED; script finished without errors"
        )
        return

    init_db()
    accounts = load_config()
    days_threshold = _float_env("STOCK_MONITOR_DAYS_THRESHOLD", DEFAULT_DAYS_THRESHOLD)
    min_avg_daily_orders = _float_env(
        "STOCK_MONITOR_MIN_AVG_DAILY_ORDERS", DEFAULT_MIN_AVG_DAILY_ORDERS
    )
    wb_enabled = _bool_env("STOCK_MONITOR_WB_ENABLED", False)
    logging.info("Stock Monitor WB enabled=%s", wb_enabled)

    all_rows = []
    problematic_rows = []

    for acc in accounts:
        marketplace = acc.get("marketplace")
        account_name = acc.get("name")
        account_id = _normalize_account_id(account_name)
        if account_id not in ALLOWED_ACCOUNT_IDS:
            continue

        stocks, orders_map = _get_data_for_account(
            account_id,
            marketplace,
            client_id=acc.get("client_id"),
            api_key=acc.get("api_key"),
            wb_enabled=wb_enabled,
        )
        logging.info(
            "Stock Monitor source loaded: account=%s marketplace=%s stock_rows=%s order_rows=%s",
            account_name,
            marketplace,
            len(stocks),
            len(orders_map),
        )
        combined_items = _combine_stock_and_orders(marketplace, account_name, stocks, orders_map)
        rows_to_save, bad_rows = build_stock_monitor_rows(
            combined_items,
            min_avg_daily_orders=min_avg_daily_orders,
            days_threshold=days_threshold,
        )
        all_rows.extend(rows_to_save)
        problematic_rows.extend(bad_rows)

    save_stock_monitor_rows([_to_db_tuple(row) for row in all_rows])
    logging.info("Stock monitor rows saved: %s", len(all_rows))

    if not problematic_rows:
        logging.info("No problematic items found; email not sent")
        return

    recipients = normalize_stock_monitor_recipients(os.getenv("STOCK_MONITOR_EMAILS"))

    email_text = build_stock_monitor_email_text(problematic_rows, days_threshold)
    report_date = datetime.now().strftime("%d.%m.%Y")
    sent = send_email(
        f"Проверка остатков за {report_date}",
        email_text,
        recipients=recipients,
    )
    if sent:
        logging.info("Stock monitor email sent")
    else:
        logging.warning("Stock monitor email was not delivered")


if __name__ == "__main__":
    main()
