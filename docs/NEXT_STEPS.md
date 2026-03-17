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
10. ~~Stage 2: минимальная очистка main (безопасный доступ к acc, константа MARKETPLACE_OZON)~~
11. ~~Stage 2: батчинг save_prices через executemany()~~
12. ~~Подготовка к внешнему планированию (main как entry point, README: ручной запуск + Task Scheduler/cron)~~
13. ~~Защита от двойного запуска (lock-файл, services/run_lock.py)~~
14. ~~Снижение ложных алертов (sanity: current_price > 0, порог по % скачка в price_analyzer)~~
15. ~~Cooldown алертов (alert_state.py, should_send_alert / update_alert_state, только отправка в Telegram)~~
16. ~~Логирование в файл с ротацией (logs/, price_monitor.log, RotatingFileHandler, консоль сохранена)~~
17. ~~Мульти-аккаунт: документирование формата config/accounts.json, уникальность name, безопасная обработка нескольких аккаунтов~~
18. ~~Cooldown по (marketplace, account, sku): составной ключ в alert_state, правки в main~~
19. ~~Итог запуска в лог (Run summary: счётчики аккаунтов, цен, алертов)~~
20. Продолжить Stage 2/3 по CHECKLIST при необходимости
21. ~~Health warnings при пустых products/prices (логирование, без прерывания)~~
22. ~~Placeholder WB-клиента (wb_client.py, ветка в main: wildberries — skip с информационным сообщением)~~
23. ~~Пороги алертов в .env (ALERT_THRESHOLD_PERCENT, ALERT_COOLDOWN_MINUTES, MAX_ALERT_CHANGE_PERCENT)~~
24. ~~Стартовое уведомление в Telegram; опциональный итог запуска (SEND_RUN_SUMMARY)~~
25. ~~Price Intelligence MVP: price_intelligence.py + report_price_intelligence.py (отчёт за 24 ч, без интеграции в main)~~
26. ~~API retry logic (Ozon), API timeout 20 s (Ozon + Telegram), индекс БД для аналитики~~
27. ~~Wildberries: базовый клиент (wb_client.py), интеграция в main~~

## Rule for every work session
At the start:
- read PROJECT_CONTEXT.md
- read CURRENT_STATUS.md
- read NEXT_STEPS.md
- read relevant code files

Future:
- добавить поддержку нескольких маркетплейсов (Ozon #2, дополнительные аккаунты WB)
- возможно внедрить adapter layer для marketplace API
- **Wildberries:** пагинация cards/list и чанки nmList для цен реализованы. Дальше: мониторинг остатков, учёт лимитов/rate limit, стабильность API
- **SEND_STARTUP_MESSAGE:** опция true/false для включения/отключения стартового уведомления в Telegram
- **Ozon pagination:** пагинация при >1000 товаров/цен (last_id для products, чанки для prices)
- **Базовые автотесты:** pytest для config_loader, валидации price_history, price_analyzer, alert_state
- **Константы маркетплейсов:** вынести в один модуль (unify marketplace constants)
- **load_dotenv:** уменьшить повторные вызовы где это безопасно
- **Price War Detector:** детекция SKU с быстрой конкурентной реакцией цен (частые колебания, снижение цен, высокая волатильность). Строится поверх price_history и Price Intelligence layer
- **Гайд по Windows Task Scheduler:** готовый пошаговый чеклист настройки для проекта

At the end:
- update CURRENT_STATUS.md
- update NEXT_STEPS.md
- summarize what changed
