import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.wb_sku_display import WbSkuDisplayMapper, display_wb_sku


def test_display_wb_sku_fallback():
    assert display_wb_sku("2935292", {"2935292": "GG001"}) == "GG001"
    assert display_wb_sku("2935292", {}) == "2935292"
    assert display_wb_sku("GG001", {"2935292": "GG001"}) == "GG001"


def test_mapper_display_sku():
    mapper = WbSkuDisplayMapper()
    mapper._by_account["wb_1"] = {"100": "FF225"}
    assert mapper.display_sku("wb_1", "100", "wildberries") == "FF225"
    assert mapper.display_sku("wb_1", "999", "wildberries") == "999"
    assert mapper.display_sku("ozon_1", "GG001", "ozon") == "GG001"


if __name__ == "__main__":
    test_display_wb_sku_fallback()
    test_mapper_display_sku()
    print("wb_sku_display self-check: OK")
