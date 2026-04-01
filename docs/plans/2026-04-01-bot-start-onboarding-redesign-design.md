# Design: Bot /start Redesign + Onboarding Mini App

**Date:** 2026-04-01
**Status:** Approved

## Overview

Упрощение входа: бот становится только точкой входа и каналом уведомлений. Вся регистрация — в Mini App. Онбординг переделан на три шага (имя → ниша → первый клиент).

---

## Часть A — Бот /start

### Что отключается

**`master_bot.py` → `setup_dispatcher()`:**
- Убрать `dp.message.outer_middleware(common.HomeButtonMiddleware())`
- Убрать `include_router` для: `registration`, `orders`, `clients`, `marketing`, `reports`, `settings`
- Оставить только `dp.include_router(common.router)`

**`common.py` — комментировать, не удалять:**
- `HomeButtonMiddleware`
- `show_home()`
- `build_home_text()`
- `cb_home` callback handler
- Импорты `home_master_kb`, `home_reply_kb`, `MasterRegistration`

### Новый `cmd_start` и `cmd_home`

Оба показывают одно и то же: баннер + caption + InlineKeyboard с WebApp кнопкой.

- Зарегистрированный мастер: `"Привет, {name}! 👋\n\nОткрой приложение, чтобы продолжить работу."`
- Новый пользователь: общий текст о продукте

### Баннер

Генерируется через `scripts/generate_banner.py` (Pillow).
- Размер: 1280×640px
- Сохраняется как `assets/welcome_banner.png`
- В коде: `FSInputFile("assets/welcome_banner.png")`

---

## Часть B — База данных

### Миграция

Файл: `migrations/001_onboarding_flags.sql`

```sql
ALTER TABLE masters ADD COLUMN onboarding_skipped_first_client BOOLEAN DEFAULT FALSE;
ALTER TABLE masters ADD COLUMN onboarding_banner_shown BOOLEAN DEFAULT FALSE;
```

### `database.py`

- `Master` dataclass: добавить два поля `bool = False`
- `_parse_master_row`: добавить маппинг
- `ALLOWED_MASTER_FIELDS`: добавить оба ключа

---

## Часть C — Онбординг Mini App

### Флоу

```
Шаг 1 (имя)
  → Шаг 2 (ниша — чипсы)
  → [300ms автопереход]
  → POST /api/master/register {name, sphere}  ← создание мастера
  → Шаг 3 (первый клиент)
  → "Добавить" → POST /api/master/clients + POST /api/master/orders → Финал
  → "Пропустить" → PUT /api/master/profile {onboarding_skipped_first_client: true} → Финал
```

### Шаг 1 — Имя

- Заголовок: "Как тебя зовут?"
- Подпись: "Будем обращаться по имени"
- Placeholder: "Например: Анна"
- Кнопка: "Продолжить" (disabled пока пусто)

### Шаг 2 — Ниша

- Заголовок: "Чем занимаешься?"
- Подпись: "Настроим шаблоны напоминаний под тебя"
- Чипсы (flex-wrap):
  - Клининг
  - Химчистка мебели и ковров
  - Парикмахер и барбер
  - Маникюр и бьюти-услуги
  - Груминг и животные
  - Массаж
  - Ремонт бытовой техники
  - Мастер на час, мелкий ремонт
  - Репетитор
  - Фотограф и видеограф
  - Психолог
  - Садовник
  - Другое
- Тап на чипс → highlight (accent color) + haptic
- "Другое" → поле свободного ввода + кнопка "Продолжить"
- Любой другой → автопереход 300ms (вызов POST /register)

### Шаг 3 — Первый клиент

- Заголовок: "Добавим первого клиента?"
- Подпись: "Увидишь как придёт напоминание — это главная фишка"
- Поля: имя (text), телефон (tel, "+7 999 123 45 67"), дата (date, default=завтра), время (time)
- "Добавить и продолжить" (disabled пока не все поля заполнены):
  1. `POST /api/master/clients {name, phone}`
  2. `POST /api/master/orders {client_id, scheduled_date, scheduled_time, services: []}`
- "Пропустить": `PUT /api/master/profile {onboarding_skipped_first_client: true}`

### Финал

- Иконка ✅
- Заголовок: "Всё готово, {name}!"
- Подпись (клиент добавлен): "Напоминание отправится клиенту автоматически — можешь проверить"
- Подпись (пропустил): "Добавь первого клиента — это займёт 30 секунд"
- Кнопка: Telegram MainButton "Начать работу" → `onRegistered()`
- Убрать: блок с инвайт-ссылкой

---

## API — правки

### `POST /api/master/register`

Уже принимает `sphere: Optional[str]` — **ничего менять не нужно**.

### `POST /api/master/orders` — убрать валидацию

`orders.py:107-108` — удалить строки:
```python
if not body.services:
    raise HTTPException(status_code=400, detail="At least one service is required")
```
При `services=[]`: `order_items=[]`, `amount_total=0`.

---

## Критерии готовности

1. `/start` → баннер + кнопка (одинаково для новых и зарегистрированных)
2. Кнопка "Домой" не появляется
3. FSM регистрации не запускается
4. Онбординг: имя → ниша → автопереход → клиент → финал
5. "Другое" → поле ввода
6. Клиент+заказ создаются без услуг (amount=0)
7. Флаг `onboarding_skipped_first_client` сохраняется в БД
8. `npm run build` без ошибок
