# ARCHITECTURE

## Purpose
Store and process marketplace prices for later monitoring and automation.

## Current core flow
1. Fetch prices from source
2. Normalize records
3. Save into database
4. Compare with previous data
5. Prepare outputs for alerts/reporting (with minimal sanity: invalid current price and unrealistically large change % are skipped for alerts only)

## Multi-account configuration
- **config/accounts.json** lists multiple accounts (see README for format). Each account has **marketplace** and **name**; **name** is the unique identifier used in cache, DB, and alerts.
- One run processes all configured accounts in sequence. Data is isolated by (marketplace, account name). Failure of one account does not stop the others.
- **Alert cooldown** state (alert_state.json) is keyed by `marketplace|account|sku` so the same SKU in different accounts has independent cooldown.

## Current data model
Table: price_history

Fields:
- id
- marketplace
- account
- sku
- product_id
- price
- created_at

## Architectural rules
- DB access should be isolated from business logic
- No duplicated DB connection logic if it can be centralized
- Constants must not be hardcoded repeatedly
- Functions should have one clear responsibility
- Validation should happen before saving data
- Logging should be added for key operations and failures

## Near-term target structure
- db layer
- source adapters / marketplace clients (Ozon implemented; Wildberries: placeholder module `clients/wb_client.py` exists, not implemented yet)
- price normalization layer
- monitoring/comparison layer
- alert/reporting layer
- **Price Intelligence (MVP):** separate reporting layer in `services/price_intelligence.py`; reads `price_history` only, produces text report (top price changes, most active SKUs, anomaly flags). Entry point: `report_price_intelligence.py` (not integrated into main monitoring flow).

## Scheduling
- Regular runs are done by an **external scheduler** (e.g. Windows Task Scheduler, cron). The app has no in-process scheduler: each run executes one pass and exits.
- At the end of each run a **run summary** is logged (accounts processed/skipped, prices fetched, alerts detected/sent/suppressed).
- **Overlapping runs**: a simple lock file (`price_monitor.lock`) prevents two instances from running at once. Acquired on start (exclusive create), released in `finally` so it is always removed on normal or error exit. If the process is killed, the file may remain and can be removed manually.

## Reliability and performance
- **API:** Ozon client uses retries (up to 3 attempts, 2 s delay) and a 20 s timeout; failures are logged and re-raised after last attempt. Telegram notifier uses 20 s timeout.
- **Analytics:** Index `idx_price_history_lookup` on `price_history(marketplace, account, sku, created_at)` is created in `init_db()` to speed up Price Intelligence and other time-window queries.

## Non-goals right now
- premature micro-optimization
- overengineering
- moving away from SQLite too early
