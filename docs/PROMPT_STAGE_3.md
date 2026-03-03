# Промпт для Claude Code — Этап 3: Функционал заказов + Google Calendar

## Контекст
Проект: Master CRM Bot. Этапы 1 и 2 завершены.
Прочитай SPEC.md и UI_SPEC.md перед началом.

---

## Задача
Реализовать полный цикл заказов + интеграцию с Google Calendar.

---

## FSM «Создать заказ» (7 шагов)

**Шаг 1 — Поиск клиента**
Ввод текста → поиск по имени И телефону (LIKE). Результаты кнопками.
Если не найден → кнопка «+ Создать нового клиента» → мини-FSM:
имя → телефон → ДР (пропустить) → продолжить создание заказа.

**Шаг 2 — Адрес**
Предложить последний адрес клиента кнопкой или ввести новый текстом.

**Шаг 3 — Дата**
Инлайн-календарь. Прошедшие даты доступны.

**Шаг 4 — Время (только кнопками)**
Сначала час (8–19), потом минуты (00 / 30). Две отдельных клавиатуры.

**Шаг 5 — Услуги**
Кнопки из справочника мастера + «✏️ Своя услуга» (ввод текстом).
Можно добавить несколько. Список обновляется после каждого добавления.
Кнопка «✅ Готово» завершает выбор.

**Шаг 6 — Сумма**
Ввод текстом. Валидация: положительное целое.

**Шаг 7 — Подтверждение**
Показать всё что выбрано + кнопки «✅ Создать» / «✏️ Изменить» / «❌ Отмена».
«Изменить» → выбор поля → возврат к нужному шагу.

**После создания:**
1. Запись в orders (статус confirmed) + order_items
2. Событие в Google Calendar (если подключён)
3. Уведомление клиенту в client_bot (если есть tg_id)
4. Обновить Home мастера

---

## FSM «Провести заказ»

1. Предложить сумму из заказа → подтвердить или изменить
2. Тип оплаты кнопками: Наличные / Карта / Перевод / По счёту
3. Списать бонусы? — показывать только если bonus_enabled=true И баланс > 0
   - Валидация: не больше баланса И не больше bonus_max_spend% от суммы
4. Подтверждение с итогами → провести

**Расчёт начисления:**
```python
bonus_accrued = round((amount_total - bonus_spent) * bonus_rate / 100)
```

**После проведения:**
1. orders: статус done, суммы, оплата, бонусы, done_at
2. master_clients: bonus_balance, total_spent, last_visit
3. bonus_log: записи spend и accrual
4. Удалить событие из GC
5. Уведомление клиенту
6. Обновить Home

---

## FSM «Перенести заказ»
Календарь → час → минуты → подтверждение (было/стало).
После: обновить GC + уведомить клиента.

---

## FSM «Отменить заказ»
Быстрые кнопки причины: «Клиент отменил» / «Мастер не может» / «Своя» / «Пропустить».
После: статус cancelled + удалить из GC + уведомить клиента.

---

## Google Calendar (google_calendar.py)

OAuth flow через настройки мастера:
- Кнопка «📅 Google Calendar» в настройках
- Генерируем OAuth URL → мастер авторизует → сохраняем credentials в masters.gc_credentials
- Показываем статус подключения и email аккаунта

Функции модуля:
```python
async def get_oauth_url(master_id) -> str
async def exchange_code(master_id, code) -> bool
async def create_event(master_id, order, client) -> str | None  # возвращает event_id
async def update_event(master_id, event_id, new_dt) -> bool
async def delete_event(master_id, event_id) -> bool
async def get_calendar_account(master_id) -> str | None
```

Формат события:
```python
{
  "summary": f"{client.name} — {', '.join(services)}",
  "description": f"📞 {client.phone}\n📍 {address}\n🛠 {services}\n💰 {amount} ₽",
  "start": {"dateTime": scheduled_at.isoformat(), "timeZone": "Europe/Moscow"},
  "end": {"dateTime": (scheduled_at + timedelta(hours=2)).isoformat(), "timeZone": "Europe/Moscow"}
}
```

**Важно:** GC опционален. Если не подключён или ошибка API — заказ создаётся в БД без ошибки. Логируем, показываем предупреждение мастеру.

---

## Уведомления клиенту (notifications.py)

Четыре функции:
```python
async def notify_order_created(bot, client, order, master)
async def notify_order_moved(bot, client, order, old_dt)
async def notify_order_cancelled(bot, client, order)
async def notify_order_done(bot, client, order, bonus_accrued)
```

Отправлять через client_bot (не master_bot).
Если клиент заблокировал бота — перехватить исключение, не ломать основной flow.
Отправлять только если client.tg_id is not None.

Тексты:
- **Создан:** дата, время, адрес, услуги, сумма, контакты мастера
- **Перенесён:** было/стало, адрес, контакты мастера
- **Отменён:** дата, услуги, причина (если есть), контакты мастера
- **Выполнен:** услуги, сумма, начислено бонусов, новый баланс

---

## Новые функции в database.py
```python
async def create_order(master_id, client_id, address, scheduled_at, services, amount_total) -> Order
async def update_order_status(order_id, status, **kwargs) -> bool
async def update_order_schedule(order_id, new_scheduled_at) -> bool
async def apply_bonus_transaction(master_id, client_id, order_id, bonus_spent, bonus_accrued) -> tuple[int, int]
async def save_gc_credentials(master_id, credentials_json) -> None
async def get_gc_credentials(master_id) -> str | None
async def save_gc_event_id(order_id, event_id) -> None
```

---

## Критерии проверки

1. Создать заказ с существующим клиентом — все 7 шагов работают
2. Создать заказ с новым клиентом — создаётся прямо в процессе
3. Время только кнопками: сначала час, потом минуты
4. «Изменить» на шаге подтверждения — возвращает к нужному шагу
5. Провести заказ — сумма предлагается, бонусы начисляются корректно
6. Списание бонусов не превышает баланс и макс. % от суммы
7. Перенос — GC обновлён, клиент уведомлён
8. Отмена — GC удалён, клиент уведомлён
9. GC не подключён → всё работает без ошибок
10. OAuth flow → мастер подключает свой календарь через настройки
11. Событие GC содержит имя, адрес, телефон, услуги, сумму
12. Home обновляется после каждого действия