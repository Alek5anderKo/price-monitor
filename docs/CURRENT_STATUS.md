# CURRENT_STATUS

## Project state
Active development.

## Working approach
Hybrid:
- coding in Cursor
- architecture/review/planning in ChatGPT Project

## What is already known
- A SQLite database is used
- Core table: price_history
- Current focus: first fix errors, then optimize, then continue implementation

## Current focus
1. Verify and fix correctness issues from current code
2. Apply agreed edits safely
3. Improve project structure
4. Continue with monitoring logic

## Important notes
- Any code change must be small and reviewable
- Avoid changing several layers at once
- Keep docs updated after each completed step

## Last completed milestone
Stage 2 (optimization): в main.py — безопасный доступ к аккаунту (marketplace/name через .get(), ранний continue при отсутствии name), константа MARKETPLACE_OZON вместо литерала "ozon", использование переменных marketplace/name вместо повторных acc["marketplace"]/acc["name"]. sku_cache, telegram_notifier, config_loader без изменений. Поведение сохранено.
