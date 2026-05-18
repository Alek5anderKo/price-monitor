"""Display-only WB SKU mapping: nmId in DB/alerts state -> vendor article (GG001) in user output."""

from services.config_loader import MARKETPLACE_WILDBERIES


def display_wb_sku(sku, nm_to_article):
    """
    Map stored nmId SKU to vendor article for display.
    Falls back to original sku when mapping is missing.
    """
    raw = str(sku or "").strip()
    if not raw or not nm_to_article:
        return raw
    return nm_to_article.get(raw, raw)


class WbSkuDisplayMapper:
    """Per-account nmId->article maps from Content API (get_nm_to_article_map)."""

    def __init__(self):
        self._by_account = {}

    def load_from_accounts(self, accounts):
        from clients.wb_client import get_nm_to_article_map

        for acc in accounts or []:
            if acc.get("marketplace") != MARKETPLACE_WILDBERIES:
                continue
            name = acc.get("name")
            api_key = acc.get("api_key")
            if not name or not api_key or name in self._by_account:
                continue
            self._by_account[name] = get_nm_to_article_map(api_key)

    def display_sku(self, account, sku, marketplace=MARKETPLACE_WILDBERIES):
        if marketplace != MARKETPLACE_WILDBERIES:
            return str(sku)
        return display_wb_sku(sku, self._by_account.get(account) or {})


def format_alert_for_display(alert, mapper, account, marketplace):
    """Alert dict copy with display sku for logs (WB only; raw sku unchanged in source)."""
    if marketplace != MARKETPLACE_WILDBERIES or not isinstance(alert, dict):
        return alert
    shown = dict(alert)
    shown["sku"] = mapper.display_sku(account, alert.get("sku"), marketplace)
    return shown
