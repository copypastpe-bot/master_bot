# Отчет об ошибках и багах

**Дата:** 2026-03-06
**Статус:** Требует исправления

---

## Критические баги

### BUG-001: Неправильное извлечение времени из scheduled_at

**Файлы:**
- `src/keyboards.py:66`
- `src/master_bot.py:175`

**Описание:**
```python
# Текущий код (НЕПРАВИЛЬНО)
time_str = order.get("scheduled_at", "")[:5]
# Для "2026-03-07T19:30:00" даёт "2026-" вместо "19:30"
```

**Причина:**
`scheduled_at` хранится в ISO формате `YYYY-MM-DDTHH:MM:SS`. Время находится на позиции `[11:16]`, а не `[0:5]`.

**Исправление:**
```python
# Вариант 1: slice
time_str = order.get("scheduled_at", "")[11:16] if order.get("scheduled_at") else "—"

# Вариант 2: datetime parse (надёжнее)
from datetime import datetime
scheduled_at = order.get("scheduled_at")
if scheduled_at:
    time_str = datetime.fromisoformat(scheduled_at).strftime("%H:%M")
else:
    time_str = "—"
```

**Приоритет:** КРИТИЧЕСКИЙ
**Влияние:** Эмодзи на кнопках заказов отображаются неправильно, время показывается как "2026-"

---

### BUG-002: Регистронезависимый поиск клиентов по кириллице

**Файл:** `src/database.py:324-344`

**Описание:**
SQLite LIKE по умолчанию регистрозависим для Unicode (кириллицы). Поиск "иван" не найдёт "Иван".

**Текущий код:**
```python
cursor = await conn.execute(
    """
    SELECT c.*, mc.bonus_balance
    FROM clients c
    JOIN master_clients mc ON c.id = mc.client_id
    WHERE mc.master_id = ?
      AND (c.name LIKE ? OR c.phone LIKE ?)
    """,
    (master_id, search_pattern, search_pattern)
)
```

**Исправление:**
```python
# Вариант 1: UPPER/LOWER в запросе
cursor = await conn.execute(
    """
    SELECT c.*, mc.bonus_balance
    FROM clients c
    JOIN master_clients mc ON c.id = mc.client_id
    WHERE mc.master_id = ?
      AND (LOWER(c.name) LIKE LOWER(?) OR c.phone LIKE ?)
    """,
    (master_id, search_pattern, search_pattern)
)

# Вариант 2: Нормализация запроса в Python
query = query.lower()
search_pattern = f"%{query}%"
# + LOWER(c.name) в SQL
```

**Приоритет:** ВЫСОКИЙ
**Влияние:** Клиенты не находятся при поиске по имени

---

## Средние баги

### BUG-003: Двойное нажатие на кнопку адреса

**Файл:** `src/master_bot.py:895-907`

**Описание:**
При выборе "последнего адреса" иногда требуется несколько нажатий.

**Возможные причины:**
1. `callback.answer()` вызывается ПОСЛЕ `go_to_date_step()`, что может создавать задержку
2. `edit_home_message` может молча проглатывать ошибки

**Текущий код:**
```python
@router.callback_query(CreateOrder.address, F.data == "order:address:last")
async def order_use_last_address(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    last_address = data.get("order_last_address")

    if not last_address:
        await callback.answer("Адрес не найден")
        return

    await state.update_data(order_address=last_address)
    await go_to_date_step(callback, state)
    await callback.answer()  # <-- Вызывается ПОСЛЕ edit_home_message
```

**Исправление:**
```python
async def order_use_last_address(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()  # <-- Вызывать СРАЗУ

    data = await state.get_data()
    last_address = data.get("order_last_address")

    if not last_address:
        return

    await state.update_data(order_address=last_address)
    await go_to_date_step(callback, state)
```

**Приоритет:** СРЕДНИЙ
**Влияние:** UX проблема — нужно несколько кликов

---

### BUG-004: Валидация чисел — сообщение остаётся в чате

**Файлы:** Множественные обработчики ввода чисел

**Описание:**
При вводе некорректного значения (текст вместо числа, отрицательное число) выводится сообщение "Введите положительное число", но:
1. Сообщение пользователя не удаляется
2. Сообщение об ошибке накапливается в чате
3. FSM состояние остаётся активным (правильно), но UI не обновляется

**Пример:**
```python
except ValueError:
    await message.answer("Введите положительное целое число")
    return
```

**Исправление:**
```python
except ValueError:
    try:
        await message.delete()
    except:
        pass
    # Показать ошибку в том же сообщении или как toast
    await message.answer("❌ Введите положительное целое число", show_alert=True)
    return
```

**Приоритет:** СРЕДНИЙ
**Влияние:** Засорение чата сообщениями об ошибках

---

### BUG-005: edit_home_message молча проглатывает ошибки

**Файл:** `src/master_bot.py:233-238`

**Описание:**
```python
async def edit_home_message(callback: CallbackQuery, text: str, keyboard) -> None:
    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard)
    except TelegramBadRequest:
        pass  # Ошибка игнорируется!
```

Если редактирование не удалось (например, сообщение уже удалено), пользователь не получит никакой обратной связи, но FSM перейдёт в следующее состояние.

**Исправление:**
```python
async def edit_home_message(callback: CallbackQuery, text: str, keyboard) -> bool:
    """Returns True if edit was successful."""
    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard)
        return True
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return True  # Не критично
        logger.warning(f"Failed to edit message: {e}")
        return False
```

**Приоритет:** СРЕДНИЙ
**Влияние:** Непредсказуемое поведение при ошибках

---

## Незначительные баги

### BUG-006: Статус "new" vs "confirmed" при создании заказа

**Файл:** `src/database.py:709`

**Описание:**
Мы исправили дефолтный статус на `"new"`, но в некоторых местах может ожидаться `"confirmed"` для активных заказов.

**Требуется проверка:**
- Фильтры в `get_orders_by_date` включают `"new"`? ✓
- Логика `get_order_emoji` корректна? ✓
- Карточка заказа показывает кнопки действий для `"new"`? ✓

**Приоритет:** НИЗКИЙ (уже исправлено, нужна только верификация)

---

### BUG-007: FSM состояние при ошибке Telegram API

**Описание:**
Если Telegram API вернёт ошибку (rate limit, network error) в середине FSM, состояние может остаться в промежуточном состоянии.

**Рекомендация:**
Добавить timeout и retry логику для критичных операций.

**Приоритет:** НИЗКИЙ

---

## План исправления

### Фаза 1 — Критические баги (немедленно)

| # | Баг | Действие | Оценка |
|---|-----|----------|--------|
| 1 | BUG-001 | Исправить извлечение времени в keyboards.py и master_bot.py | 5 мин |
| 2 | BUG-002 | Добавить LOWER() в SQL запрос поиска клиентов | 5 мин |

### Фаза 2 — Средние баги (в течение дня)

| # | Баг | Действие | Оценка |
|---|-----|----------|--------|
| 3 | BUG-003 | Переместить callback.answer() в начало обработчиков | 15 мин |
| 4 | BUG-004 | Добавить удаление сообщения при ошибке валидации | 20 мин |
| 5 | BUG-005 | Улучшить обработку ошибок в edit_home_message | 10 мин |

### Фаза 3 — Тестирование

После исправления:
1. Проверить отображение эмодзи в списке заказов
2. Проверить поиск клиентов по имени (кириллица, разный регистр)
3. Проверить выбор адреса одним кликом
4. Проверить ввод некорректных значений в числовые поля

---

## Итого

- **Критических багов:** 2
- **Средних багов:** 3
- **Незначительных багов:** 2
- **Общее время на исправление:** ~1 час
