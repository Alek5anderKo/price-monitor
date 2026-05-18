import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.stock_monitor_analyzer import build_stock_monitor_rows


def _item(stock, o7=0, o14=0, o30=0):
  return {
    "marketplace": "ozon",
    "account": "ozon_1",
    "sku": "TEST-SKU",
    "product_id": 1,
    "current_stock": stock,
    "orders_7": o7,
    "orders_14": o14,
    "orders_30": o30,
  }


def test_zero_stock_zero_orders_no_alert():
  _, bad = build_stock_monitor_rows([_item(0, 0, 0, 0)], min_avg_daily_orders=0.0, days_threshold=14.0)
  assert bad == []


def test_positive_stock_zero_orders_no_alert():
  _, bad = build_stock_monitor_rows([_item(10, 0, 0, 0)], min_avg_daily_orders=0.0, days_threshold=14.0)
  assert bad == []


def test_positive_stock_and_orders_can_alert_when_below_threshold():
  # avg_30 = 30/30 = 1.0 -> days_left = 10/1 = 10 < 14
  _, bad = build_stock_monitor_rows(
    [_item(10, 0, 0, 30)],
    min_avg_daily_orders=0.0,
    days_threshold=14.0,
  )
  assert len(bad) == 1
  assert bad[0]["current_stock"] == 10
  assert bad[0]["days_left"] == 10.0


def test_no_alert_when_days_left_above_threshold():
  # avg_7 = 7/7 = 1 -> days_left = 100
  _, bad = build_stock_monitor_rows(
    [_item(100, 7, 0, 0)],
    min_avg_daily_orders=0.0,
    days_threshold=14.0,
  )
  assert bad == []


if __name__ == "__main__":
  test_zero_stock_zero_orders_no_alert()
  test_positive_stock_zero_orders_no_alert()
  test_positive_stock_and_orders_can_alert_when_below_threshold()
  test_no_alert_when_days_left_above_threshold()
  print("stock_monitor_analyzer self-check: OK")
