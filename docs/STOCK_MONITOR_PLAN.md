# STOCK MONITOR PLAN

## Цель
Добавить безопасный отдельный контур контроля остатков без изменения текущей логики Price Monitor.

## Кабинеты
- ozon_1
- ozon_2
- wb_1

## FBO
Текущий каркас ориентирован на метрики FBO.

## Остаток
Используется общий остаток по товару без детализации по кластерам.

## Метрика
Основная метрика спроса: количество заказов.

## Периоды
Расчет заказов по окнам:
- 7 дней
- 14 дней
- 30 дней

## Wildberries (Stock Monitor): источники API
- **Остатки:** Seller Analytics `POST /api/analytics/v1/stocks-report/wb-warehouses` (нужны права категории токена, связанной с Analytics).
- **Заказы:** Statistics API `GET https://statistics-api.wildberries.ru/api/v1/supplier/orders` с `dateFrom` ≈ 30 суток назад (RFC3339; в коде для расчёта `dateFrom` используется **UTC+3** как московское время без зависимости от системной базы IANA/tzdata), `flag=0` (записи с `lastChangeDate` ≥ `dateFrom`). Seller Analytics `POST .../sales-funnel/products` для Stock Monitor **не** используется из‑за жёсткого глобального лимитера (частые 429). Ответ Statistics — массив заказов; при необходимости допускается пагинация по `lastChangeDate` последней строки (лимит ~80k строк на запрос). Окна **7 / 14 / 30** дней считаются **локально** по моменту заказа: поле **`date`**, при отсутствии — **`lastChangeDate`**; строки с **`isCancel`: true** не учитываются. Ключ SKU для агрегации: **`vendorCode`**, иначе **`supplierArticle`**, иначе **`nmId`** — тот же приоритет, что и при разборе строк остатков в `wb_stock_client.py`. Для доступа к Statistics нужна категория токена **Statistics** (отдельно от Analytics).

## Формула
- avg_7 = orders_7 / 7
- avg_14 = orders_14 / 14
- avg_30 = orders_30 / 30
- avg_daily_orders = max(avg_7, avg_14, avg_30)
- days_left = current_stock / avg_daily_orders

## Порог
Товар попадает в отчет, если расчетный запас меньше 14 дней.

## Канал уведомления
Только e-mail (без Telegram).

## Настройки .env
- `STOCK_MONITOR_ENABLED` — включает/выключает модуль (по умолчанию `false`).
- `STOCK_MONITOR_USE_TEST_FALLBACK` — разрешает подстановку тестовых данных Ozon/WB при пустом/недоступном API (по умолчанию **`false`**). В production оставлять `false`, чтобы не отправлять отчёты с искусственными остатками/заказами.
- `STOCK_MONITOR_WB_ENABLED` — включает/выключает контур Wildberries в Stock Monitor (по умолчанию `false`).
- `STOCK_MONITOR_DAYS_THRESHOLD` — порог по дням запаса (по умолчанию `14`).
- `STOCK_MONITOR_MIN_AVG_DAILY_ORDERS` — минимальная средняя дневная скорость продаж для участия SKU в расчете (по умолчанию `0.1`).
- `STOCK_MONITOR_EMAILS` — получатели отчета через запятую; если пусто, используются стандартные получатели e-mail канала.

## Частота запуска
1 раз в день отдельным скриптом `send_stock_monitor_report.py`.

## Этапы внедрения
1. Каркас (заглушки клиентов, анализатор, сохранение в БД, e-mail отчет).
2. Подключение Ozon API.
3. Подключение Wildberries API.
4. Регулярный запуск через cron/Task Scheduler.

## Временные вещи / что нужно убрать или заменить перед production
- Тестовые fallback-данные Ozon/WB доступны **только** при `STOCK_MONITOR_USE_TEST_FALLBACK=true` (для локальной отладки). По умолчанию `false` — подстановки нет.
- Wildberries в текущем этапе все еще работает на заглушках и должен быть переведен на реальный API до production.
- `scripts/test_email.py` является только диагностическим скриптом и не относится к регулярному production-процессу.
- В `stock_monitor_history` уже могут быть локальные тестовые записи; перед production нужно отделить/очистить тестовые данные.
- Правило production: `STOCK_MONITOR_USE_TEST_FALLBACK=false` — не подставлять тестовые данные и не строить отчёт на их основе; при пустом API логировать и не отправлять e-mail с фиктивными цифрами (если после расчёта нет проблемных SKU — письмо не уходит).
- Wildberries временно отключен до получения токена типа Personal/Service (`STOCK_MONITOR_WB_ENABLED=false`).
- Причина временного отключения WB: Base token не разрешен для нужных Analytics endpoints.
