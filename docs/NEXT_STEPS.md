# NEXT_STEPS

## Immediate next actions
1. ~~Review current Python files in Cursor~~
2. ~~Compare code with docs/CHECKLIST.md~~
3. ~~Fix correctness issues first (db.py, price_analyzer.py)~~
4. ~~Stage 1: connection/error handling в config_loader, sku_cache, telegram_notifier, init_db, get_last_price/get_day_start_price~~
5. ~~Stage 1: устойчивость main по аккаунтам, save_prices при None/не-списке, cache write errors, telegram message/request errors~~
6. ~~Stage 1: надёжность Telegram (timeout, RequestException, проверка status_code); save_prices при пустом prices~~
7. ~~Stage 2: оптимизация запросов к БД в price_analyzer (bulk-запросы вместо 2N)~~
8. ~~Минимальная очистка после Stage 2 (явные ph.account в SQL, удаление diff.txt)~~
9. ~~Stage 2: базовое логирование (basicConfig в main, замена print в main, telegram_notifier, sku_cache)~~
10. Продолжить Stage 2 по CHECKLIST: константы, при необходимости — батчинг в save_prices

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
