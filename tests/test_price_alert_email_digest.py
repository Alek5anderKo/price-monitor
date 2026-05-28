import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.price_alert_email_digest import (
    build_price_alert_digest_text,
    price_alert_digest_subject,
)


def test_digest_subject_format():
    run_at = datetime(2026, 5, 19, 11, 30)
    assert price_alert_digest_subject(run_at) == "Изменение цен за 19.05.2026 11:30"


def test_digest_body_grouping():
    items = [
        {
            "marketplace": "ozon",
            "account": "ozon_1",
            "display_sku": "GG700",
            "old_price": 5822.0,
            "new_price": 4457.0,
            "change": -22.9,
            "type": "day_start",
        },
        {
            "marketplace": "wildberries",
            "account": "wb_1",
            "display_sku": "GG732",
            "old_price": 3297.0,
            "new_price": 3372.08,
            "change": 2.28,
            "type": "day_start",
        },
    ]
    text = build_price_alert_digest_text(items)
    assert "GG700" in text
    assert "GG732" in text
    assert "/ day_start" in text
    assert "ozon_1 (Трейд)" in text


if __name__ == "__main__":
    test_digest_subject_format()
    test_digest_body_grouping()
    print("price_alert_email_digest self-check: OK")
