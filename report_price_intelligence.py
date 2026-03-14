"""
Price Intelligence Report — text summary from price_history (last 24 hours).
Run from project root: python report_price_intelligence.py
"""
from services.price_intelligence import (
    REPORT_HOURS,
    get_top_price_changes,
    get_most_active_skus,
    get_anomalies,
)


def main():
    top = get_top_price_changes(hours=REPORT_HOURS)
    active = get_most_active_skus(hours=REPORT_HOURS)
    anomalies = get_anomalies(hours=REPORT_HOURS)

    print("Price Intelligence Report")
    print("Period: last 24 hours")
    print()

    print("Top price changes:")
    if not top:
        print("  (no data)")
    else:
        for i, row in enumerate(top, 1):
            print(
                "  %s. %s | %s | SKU %s: %.2f -> %.2f (change %s%%)"
                % (
                    i,
                    row["marketplace"],
                    row["account"],
                    row["sku"],
                    row["min_price"],
                    row["max_price"],
                    row["change_pct"],
                )
            )
    print()

    print("Most active SKUs:")
    if not active:
        print("  (no data)")
    else:
        for i, row in enumerate(active, 1):
            print(
                "  %s. %s | %s | SKU %s: %s price records"
                % (i, row["marketplace"], row["account"], row["sku"], row["count"])
            )
    print()

    print("Potential anomalies:")
    if not anomalies:
        print("  (none)")
    else:
        for a in anomalies:
            if a["type"] == "large_spread":
                print(
                    "  [large spread] %s | %s | SKU %s: spread %.2f%% (min %.2f, max %.2f)"
                    % (
                        a["marketplace"],
                        a["account"],
                        a["sku"],
                        a["spread_pct"],
                        a["min_price"],
                        a["max_price"],
                    )
                )
            else:
                print(
                    "  [frequent changes] %s | %s | SKU %s: %s records in period"
                    % (
                        a["marketplace"],
                        a["account"],
                        a["sku"],
                        a["record_count"],
                    )
                )
    print()
    print("Report complete.")


if __name__ == "__main__":
    main()
