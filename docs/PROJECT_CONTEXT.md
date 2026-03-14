# PROJECT_CONTEXT

## Project
Price Monitor

## Goal
Build a reliable price monitoring system for marketplaces that:
- regularly fetches current prices
- stores price history
- tracks price changes by marketplace/account/product
- allows later automation, alerts, analytics, and reporting

## Current working mode
Hybrid mode:
- implementation in Cursor
- architecture, review, planning, checklist and decisions in ChatGPT Project

## Main principles
1. Small safe steps
2. Fix correctness first
3. Then optimize
4. Then continue implementation
5. Do not break existing behavior without reason
6. All important changes must be reflected in docs/CURRENT_STATUS.md and docs/NEXT_STEPS.md

## Technical baseline
- Python
- SQLite at current stage
- Price history table is already planned
- Marketplace/account/SKU/product_id/price/timestamp are core entities

## Priorities
1. Correctness of code and logic
2. Stable storage
3. Clean architecture
4. Error handling and logging
5. Extensibility for future integrations

## Development rule
Before changing code:
- read related files
- check docs/CURRENT_STATUS.md
- check docs/NEXT_STEPS.md
- keep architecture consistent
