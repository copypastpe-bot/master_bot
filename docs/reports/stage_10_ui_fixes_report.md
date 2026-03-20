# Отчет: Правки UI — Этап A

**Дата:** 2026-03-06
**Коммит:** `08c1cde` (Stage 10: UI fixes and order confirmation workflow)

---

## Выполненные задачи

### Правка 1 — Постоянная Reply-кнопка «🏠 Домой» ✅

**Что сделано:**
- Добавлена `home_reply_kb()` в `keyboards.py` с `is_persistent=True`
- Отправляется при `/start` в обоих ботах
- Реализован `HomeButtonMiddleware` как `outer_middleware` для перехвата кнопки ДО FSM-обработчиков
- `state.clear()` прерывает любой активный FSM
- Сообщение пользователя удаляется
- Home экран показывается с `force_new=True` (внизу чата)

**Файлы:**
- `src/master_bot.py` — HomeButtonMiddleware, show_home(force_new)
- `src/client_bot.py` — HomeButtonMiddleware, show_home(force_new)
- `src/keyboards.py` — home_reply_kb()

---

### Правка 2 — Завершение сценариев возвратом в родительское меню ✅

**Что сделано:**
Обновлены все FSM completion handlers:

| Сценарий | Возврат | Статус |
|----------|---------|--------|
| Создать заказ | Экран «Заказы» за день | ✅ |
| Провести заказ | Карточка заказа | ✅ |
| Перенести заказ | Карточка заказа | ✅ |
| Отменить заказ | Экран «Заказы» | ✅ |
| Добавить клиента | Экран «Клиенты» | ✅ |
| Редактировать клиента | Карточка клиента | ✅ |
| Заметка клиента | Карточка клиента | ✅ |
| Бонусы клиента | Экран бонусов | ✅ |
| Рассылка | Экран «Маркетинг» | ✅ |
| Акция | Экран «Маркетинг» | ✅ |
| Период отчётов | Экран «Отчёты» | ✅ |
| Редактировать профиль | Экран «Профиль» | ✅ |
| Бонусная программа | Экран бонусов | ✅ |
| Услуги | Справочник услуг | ✅ |

**Файлы:**
- `src/master_bot.py` — все FSM completion handlers

---

### Правка 4 — Выполненные заказы остаются в расписании ✅

**Что сделано:**
- `get_orders_by_date()` теперь возвращает ВСЕ заказы (all_statuses=True)
- Добавлена функция `get_order_emoji()` в `keyboards.py`
- Эмодзи статусов на кнопках заказов:
  - 🆕 new
  - 📌 confirmed
  - ✅ done
  - ❌ cancelled
  - 📅 moved
- Карточка выполненного заказа: кнопки действий скрыты, есть «Перейти к клиенту»

**Файлы:**
- `src/database.py` — get_orders_by_date(all_statuses)
- `src/keyboards.py` — get_order_emoji(), order_card_kb()
- `src/master_bot.py` — show_orders_screen()

---

### Правка 5 — Метка «❓» на неподтверждённых заказах ✅

**Что сделано:**
- Добавлено поле `client_confirmed` в таблицу orders (миграция 004)
- Логика эмодзи в `get_order_emoji()`:
  - Если `reminder_24h_sent=true` И `client_confirmed=false` → ❓
  - После подтверждения клиентом → 📌
- Обработчик `confirm_order:{id}` устанавливает `client_confirmed=true`

**Дополнительно реализовано (сверх ТЗ):**
- Кнопки «📅 Перенести» и «❌ Отменить» в уведомлении за 24ч
- FSM для переноса заказа клиентом (ClientRescheduleOrder)
- FSM для отмены заказа клиентом (ClientCancelOrder)
- Уведомление мастера о переносе/отмене клиентом
- Auto-confirm при переносе в пределах 24ч
- Сброс флагов для нового цикла напоминаний при переносе >24ч
- Изменён дефолтный статус заказа: `"confirmed"` → `"new"`

**Файлы:**
- `migrations/004_client_confirmed.sql`
- `src/database.py` — mark_order_confirmed_by_client(), reset_order_for_reconfirmation()
- `src/scheduler.py` — confirm_order_kb() с 3 кнопками
- `src/client_bot.py` — обработчики reschedule/cancel
- `src/states.py` — ClientRescheduleOrder, ClientCancelOrder
- `src/keyboards.py` — клавиатуры для переноса/отмены

---

### Правка 8 — Описание услуги в справочнике ✅

**Что сделано:**
- Добавлено поле `description` в таблицу services (миграция 005)
- Карточка услуги показывает описание если есть
- FSM добавления услуги: шаг «Описание» с кнопкой «Пропустить»
- Кнопка «✏️ Описание» в редактировании услуги

**Файлы:**
- `migrations/005_service_description.sql`
- `src/database.py` — Service model, create_service(), update_service()
- `src/models.py` — Service.description
- `src/master_bot.py` — ServiceAdd FSM, service card display
- `src/keyboards.py` — service_edit_kb()

---

## Известные проблемы (требуют проверки)

1. **Эмодзи статусов** — не всегда отображаются корректно
2. **Поиск клиентов** — работает по телефону, но не по имени
3. **Зависания при вводе чисел** — «Введите положительное число»
4. **Выбор адреса** — требует нескольких нажатий
5. **FSM состояния** — возможно не сбрасываются в некоторых сценариях

---

## Статистика изменений

```
 src/client_bot.py | +486 строк
 src/database.py   | +109 строк
 src/keyboards.py  | +158 строк
 src/master_bot.py | +683 строк
 src/models.py     | +1 строка
 src/scheduler.py  | +8 строк
 src/states.py     | +24 строки
 ─────────────────────────────
 Итого: +1319 строк, -150 строк
```
