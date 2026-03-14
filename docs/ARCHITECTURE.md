# ARCHITECTURE

## Purpose
Store and process marketplace prices for later monitoring and automation.

## Current core flow
1. Fetch prices from source
2. Normalize records
3. Save into database
4. Compare with previous data
5. Prepare outputs for alerts/reporting

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
- source adapters / marketplace clients
- price normalization layer
- monitoring/comparison layer
- alert/reporting layer

## Non-goals right now
- premature micro-optimization
- overengineering
- moving away from SQLite too early
