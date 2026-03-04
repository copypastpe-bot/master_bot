# Промпт: Этап 5 — Напоминания и планировщик

## Контекст
Прочитай SPEC.md перед началом.
APScheduler уже в requirements.txt. Планировщик запускается вместе с ботами.

---

## Архитектура

Создать модуль `src/scheduler.py`.
Планировщик инициализируется в `master_bot.py` и `client_bot.py` при старте.
Оба бота должны иметь доступ к одному экземпляру — передавать `bot` объекты через параметры задач.
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
```

Запуск вместе с ботом:
```python
scheduler.start()
```

---

## Задачи планировщика

### Задача 1 — Напоминание за 24 часа

**Расписание:** каждые 60 минут  
**Функция:** `send_reminders_24h(client_bot)`

Логика:
```python
# Найти заказы у которых:
# scheduled_at BETWEEN (now + 23h) AND (now + 25h)
# status IN ('new', 'confirmed')
# reminder_24h_sent = false
```

После отправки — установить `orders.reminder_24h_sent = true`.

Добавить в таблицу `orders` два новых поля:
```sql
ALTER TABLE orders ADD COLUMN reminder_24h_sent BOOLEAN DEFAULT FALSE;
ALTER TABLE ORDER ADD COLUMN reminder_1h_sent BOOLEAN DEFAULT FALSE;
```

Текст уведомления клиенту:
```
🔔 Напоминание о записи

Завтра у вас запись:
📅 {дата}, {время}
📍 {адрес}
🛠 {услуги}

Мастер: {имя мастера}
📞 {контакты мастера}
```

Кнопка под сообщением:
```
[✅ Подтверждаю запись]
```

callback_data: `confirm_order:{order_id}`

Отправлять только если:
- `client.tg_id IS NOT NULL`
- `master_clients.notify_reminders = true`

### Задача 2 — Напоминание за 1 час

**Расписание:** каждые 15 минут  
**Функция:** `send_reminders_1h(client_bot)`

Логика:
```python
# Найти заказы у которых:
# scheduled_at BETWEEN (now + 45min) AND (now + 75min)
# status IN ('new', 'confirmed')
# reminder_1h_sent = false
```

Текст уведомления клиенту:
```
⏰ Через час ваша запись!

📅 Сегодня в {время}
📍 {адрес}
🛠 {услуги}

Мастер: {имя мастера}
📞 {контакты мастера}
```

Кнопка:
```
[📞 Написать мастеру]
```

callback_data: `tg://user?id={master.tg_id}` (открывает чат с мастером)

Отправлять только если:
- `client.tg_id IS NOT NULL`
- `master_clients.notify_reminders = true`

### Задача 3 — Бонус на день рождения

**Расписание:** ежедневно в 10:00  
**Функция:** `send_birthday_bonuses(client_bot)`

Логика:
```python
# Найти клиентов у которых:
# strftime('%m-%d', birthday) = strftime('%m-%d', 'now')  # SQLite
# master.bonus_enabled = true
# master.bonus_birthday > 0
```

Для каждого клиента и каждого мастера у которого он есть:
1. Начислить `master.bonus_birthday` бонусов
2. Записать в `bonus_log` (тип `birthday`)
3. Обновить `master_clients.bonus_balance`
4. Отправить уведомление клиенту

Текст уведомления:
```
🎂 С днём рождения, {имя}!

Ваш мастер {имя мастера} дарит вам
🎁 {сумма} бонусов!

💰 Ваш баланс: {новый баланс} ₽

Используйте бонусы при следующем заказе.
```

---

## Обработчик подтверждения от клиента

В `client_bot.py` добавить обработчик callback `confirm_order:{order_id}`:
```python
@router.callback_query(F.data.startswith("confirm_order:"))
async def handle_order_confirmation(callback, ...):
```

Логика:
1. Получить `order_id` из callback
2. Проверить что заказ принадлежит этому клиенту
3. Проверить что статус `new` или `confirmed`
4. Обновить кнопку в сообщении → заменить на `✅ Запись подтверждена`
5. Отправить уведомление мастеру в `master_bot`

Текст уведомления мастеру:
```
✅ Клиент подтвердил запись!

👤 {имя клиента}
📅 {дата}, {время}
📍 {адрес}
🛠 {услуги}
```

После нажатия кнопки — редактировать сообщение клиента:
```
🔔 Напоминание о записи

📅 {дата}, {время}
📍 {адрес}
🛠 {услуги}

Мастер: {имя мастера}
📞 {контакты мастера}

✅ Вы подтвердили запись
```
(кнопка убирается, текст подтверждения добавляется)

---

## Новые функции в database.py
```python
async def get_orders_for_reminder_24h() -> list[dict]
# Возвращает заказы + данные клиента и мастера одним запросом

async def get_orders_for_reminder_1h() -> list[dict]

async def get_clients_with_birthday_today() -> list[dict]
# Возвращает клиентов + данные мастера

async def mark_reminder_sent(order_id, reminder_type: str)
# reminder_type: '24h' | '1h'

async def accrue_birthday_bonus(master_id, client_id) -> int
# Начисляет бонус, возвращает новый баланс
```

---

## Защита от дублирования

Флаги `reminder_24h_sent` и `reminder_1h_sent` в таблице `orders` — главная защита.
Дополнительно: оборачивать каждую отправку в try/except, логировать ошибки.
Если клиент заблокировал бота — перехватить `TelegramForbiddenError`, не останавливать задачу.

---

## Критерии проверки

1. Планировщик стартует вместе с ботом без ошибок
2. За 24ч до заказа клиент получает уведомление с кнопкой «Подтверждаю»
3. Повторно уведомление не отправляется (флаг reminder_24h_sent)
4. Клиент нажал «Подтверждаю» → кнопка исчезает, мастер получает уведомление
5. За 1ч клиент получает уведомление с кнопкой «Написать мастеру»
6. Повторно уведомление за 1ч не отправляется (флаг reminder_1h_sent)
7. В день рождения клиент получает бонусы и уведомление
8. День рождения не начисляется повторно (проверить через bonus_log)
9. Если клиент отключил remind в настройках — уведомления не приходят
10. Если бонусы у мастера выключены — ДР-бонус не начисляется