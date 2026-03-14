# NEXT_STEPS

## Immediate next actions
1. ~~Review current Python files in Cursor~~
2. ~~Compare code with docs/CHECKLIST.md~~
3. ~~Fix correctness issues first (db.py, price_analyzer.py)~~
4. ~~Stage 1: connection/error handling в config_loader, sku_cache, telegram_notifier, init_db, get_last_price/get_day_start_price~~
5. ~~Stage 1: устойчивость main по аккаунтам, save_prices при None/не-списке, cache write errors, telegram message/request errors~~
6. ~~Stage 1: надёжность Telegram (timeout, RequestException, проверка status_code); save_prices при пустом prices~~
7. При необходимости — оставшиеся пункты Stage 1 по CHECKLIST, затем этап 2 (оптимизация): константы, логирование

## Rule for every work session
At the start:
- read PROJECT_CONTEXT.md
- read CURRENT_STATUS.md
- read NEXT_STEPS.md
- read relevant code files

At the end:
- update CURRENT_STATUS.md
- update NEXT_STEPS.md
- summarize what changed
