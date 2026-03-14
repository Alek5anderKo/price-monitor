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
- Пороги алертов вынесены в .env: `ALERT_THRESHOLD_PERCENT`, `ALERT_COOLDOWN_MINUTES`, `MAX_ALERT_CHANGE_PERCENT` (дефолты: 1, 60, 100); при отсутствии или неверном значении используется дефолт.
- Стартовое уведомление в Telegram: одно сообщение в начале запуска (время, число аккаунтов), если аккаунты есть и Telegram настроен; при ошибке отправки — только лог.
- Опциональный итог запуска в Telegram: переменная `SEND_RUN_SUMMARY=true` включает отправку сводки в конце запуска; по умолчанию отключено.
- Price Intelligence Layer (MVP): модуль `services/price_intelligence.py` (чтение только из SQLite), отчёт `report_price_intelligence.py` — топ изменений цен, самые активные SKU, флаги аномалий (спред %, частая смена цен) за последние 24 часа; мониторинг и отчёт разделены.
- Надёжность API и аналитики: в Ozon-клиенте добавлены повторы запросов (до 3 попыток, пауза 2 с, логирование), таймаут 20 с для Ozon и Telegram; в init_db добавлен индекс `idx_price_history_lookup` для запросов по (marketplace, account, sku, created_at).
