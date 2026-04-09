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
- Пороги алертов вынесены в .env: 'LAST_PRICE_ALERT_THRESHOLD_PERCENT', 'DAY_START_ALERT_THRESHOLD_PERCENT', `ALERT_COOLDOWN_MINUTES`, `MAX_ALERT_CHANGE_PERCENT` (дефолты: 10, 20, 60, 100); при отсутствии или неверном значении используется дефолт.
- Стартовое уведомление в Telegram: одно сообщение в начале запуска (время, число аккаунтов), если аккаунты есть и Telegram настроен; при ошибке отправки — только лог.
- Опциональный итог запуска в Telegram: переменная `SEND_RUN_SUMMARY=true` включает отправку сводки в конце запуска; по умолчанию отключено.
- Price Intelligence Layer (MVP): модуль `services/price_intelligence.py` (чтение только из SQLite), отчёт `report_price_intelligence.py` — топ изменений цен, самые активные SKU, флаги аномалий (спред %, частая смена цен) за последние 24 часа; мониторинг и отчёт разделены.
- Надёжность API и аналитики: в Ozon-клиенте добавлены повторы запросов (до 3 попыток, пауза 2 с, логирование), таймаут 20 с для Ozon и Telegram; в init_db добавлен индекс `idx_price_history_lookup` для запросов по (marketplace, account, sku, created_at).
- Wildberries: клиент в `clients/wb_client.py` приведён к официальной документации WB. Один токен с правами Promotion и Цены и скидки: cards/list (Content API, scope Promotion), list/goods/filter (Prices API, scope Цены и скидки). Тело запроса cards/list — sort, cursor, filter; тело цен — nmList; разбор ответа цен — data.listGoods[], цена из sizes[0].price или sizes[0].discountedPrice. Исправлена нормализация SKU (sku как строка) для совпадения с ключами из БД при детекции алертов.
- Исправлена нормализация sku на стороне БД для надёжной детекции алертов Wildberries: ключи в словарях из `get_last_prices_bulk` и `get_day_start_prices_bulk` — всегда строки; при сохранении в `save_prices` sku записывается как строка, чтобы старые строки с целочисленным sku не приводили к пропуску алертов.
- Wildberries: пагинация cards/list (limit 100, курсор updatedAt/nmID до ответа < limit); дедупликация по str(nmID). Запросы цен при nmList > 1000 разбиваются на чанки по 1000, ответы объединяются.
- Добавлен второй канал уведомлений: e-mail (`services/email_notifier.py`, SMTP). В `main.py` добавлены флаги `SEND_TELEGRAM_ALERTS`, `SEND_EMAIL_ALERTS`, `SEND_STARTUP_MESSAGE`, `SEND_STARTUP_EMAIL`; ошибки e-mail/Telegram логируются и не роняют запуск.
- Добавлен daily e-mail report как отдельный entrypoint: `send_daily_report.py` + `services/daily_report.py`. Отчёт строится по `price_history` за день (объём, уникальные SKU/аккаунты, топ-5 ростов и снижений по first/last цене внутри связки marketplace/account/sku).
- Снижен риск попадания e-mail в спам за счёт обновления тем и текстов уведомлений без изменения бизнес-логики: для alert-писем убраны `ALERT`/капс, добавлены человекочитаемая тема и нейтральный текст с приветствием; для daily report обновлены тема и формулировки блоков, добавлена единая подпись "Автоматическое уведомление".
