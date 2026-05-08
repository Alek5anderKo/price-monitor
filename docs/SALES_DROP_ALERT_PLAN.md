# SALES DROP ALERT PLAN

## Цель
Раз в неделю находить товары с резким падением продаж при наличии остатка.

## Бизнес-условия
- Алерт не формируется, если `current_stock <= 0`.
- Правило сильного падения:
  - `previous_7_days_orders >= 10`
  - `current_7_days_orders <= previous_7_days_orders / 3`
- Правило остановки продаж:
  - `previous_7_days_orders >= 5`
  - `current_7_days_orders == 0`

## Почему исключаем current_stock <= 0
Если товара нет на остатке, снижение продаж не является аномалией спроса и не требует алерта отделу снабжения.

## Расписание
Плановый запуск — 1 раз в неделю, в пятницу утром.

## Охват этапа MVP
- Только Ozon.
- Wildberries подключается позже.
- Только e-mail канал (без Telegram).

## Периоды сравнения
- current week: последние 7 полных дней (без текущего дня)
- previous week: 7 дней перед current week

## Получатели
- `SALES_DROP_EMAILS` — если задано, отправлять туда.
- Если пусто — использовать стандартных получателей e-mail канала.

## Cron для будущего VPS
```cron
# Пятница, 08:00
0 8 * * 5 cd /path/to/Pricemonitor && python send_sales_drop_report.py >> logs/sales_drop.log 2>&1
```
