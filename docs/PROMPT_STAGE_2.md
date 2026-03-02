# Промпт для Claude Code — Этап 2: Скелет UI и навигация

## Контекст

Проект: **Master CRM Bot** — два Telegram-бота на одной SQLite БД.
- `master_bot.py` — бот для мастеров
- `client_bot.py` — бот для клиентов

Этап 1 завершён: регистрация мастера и клиента работает, БД создаётся.

Полная спецификация — `SPEC.md`
UI спецификация — `UI_SPEC.md` ← **главный документ для этого этапа**

Прочитай оба файла перед началом работы.

---

## Задача Этапа 2

Реализовать полный скелет навигации обоих ботов: все экраны, все переходы между ними, заглушки для функционала который будет в следующих этапах.

**После этого этапа:** оба бота полностью навигируемы, все кнопки работают, все экраны отображаются (пусть с заглушками данных).

---

## Ключевые технические требования

### 1. Гибридный UI

**Home** — одно постоянное сообщение на пользователя. При любой навигации оно **редактируется** (`edit_text` / `edit_reply_markup`), не создаётся новое.

**Разделы** (Заказы, Клиенты, Маркетинг, Отчёты, Настройки и их подэкраны) — редактируют то же самое Home-сообщение.

**FSM-сценарии** (ввод данных: новый заказ, добавить клиента и т.д.) — новые сообщения, которые после завершения удаляются. После FSM — Home обновляется.

### 2. Хранение message_id

Для редактирования Home нужно хранить `message_id` постоянного сообщения.
Добавь в таблицу `masters` колонку `home_message_id BIGINT` (для master_bot).
Добавь в таблицу `master_clients` колонку `home_message_id BIGINT` (для client_bot).

При первом `/start` — отправляем Home и сохраняем `message_id`.
При последующих вызовах — редактируем сохранённое сообщение.

Если сообщение не найти (удалено пользователем) — отправляем новое и обновляем `message_id`.

### 3. Callback data формат

Используй чёткий формат: `раздел:действие:параметр`

Примеры:
```
home                    — вернуться на Home
orders                  — раздел Заказы
orders:new              — новый заказ
orders:view:12          — карточка заказа #12
orders:calendar         — открыть календарь
orders:calendar:2026:3  — календарь март 2026
orders:calendar:date:2026-03-15  — выбрана дата
orders:complete:12      — провести заказ #12
orders:move:12          — перенести заказ #12
orders:cancel:12        — отменить заказ #12
clients                 — раздел Клиенты
clients:view:45         — карточка клиента #45
clients:history:45      — история клиента #45
clients:bonus:45        — бонусы клиента #45
clients:edit:45         — редактировать клиента #45
clients:note:45         — заметка клиента #45
marketing               — раздел Маркетинг
marketing:broadcast     — рассылка
marketing:promo         — акция
reports                 — раздел Отчёты
reports:today           — за сегодня
reports:week            — за неделю
reports:month           — за месяц
reports:period          — произвольный период
settings                — раздел Настройки
settings:profile        — профиль
settings:bonus          — бонусная программа
settings:services       — справочник услуг
settings:invite         — инвайт-ссылка
```

### 4. Навигация «Назад»

Каждый экран знает своего родителя. Кнопка «◀️ Назад» редактирует текущее сообщение, показывая родительский экран.

Иерархия:
```
home
├── orders
│   ├── orders:view:N → назад в orders
│   └── orders:calendar → назад в orders
├── clients
│   └── clients:view:N
│       ├── clients:history:N → назад в clients:view:N
│       └── clients:bonus:N → назад в clients:view:N
├── marketing
├── reports
└── settings
    ├── settings:profile
    ├── settings:bonus
    ├── settings:services
    └── settings:invite
```

---

## Что реализовать

### master_bot.py

#### Home экран

Функция `show_home(bot, master, message_or_callback)`:
- Получает заказы на сегодня из БД
- Формирует текст с расписанием
- Если `home_message_id` есть → `edit_message_text`
- Если нет или ошибка → `send_message` + сохранить новый `message_id`

Текст Home:
```
👋 Привет, {name}!
━━━━━━━━━━━━━━━
📅 Сегодня, {дата}:

• 10:00 — Иван П. | ул. Ленина 5
• 14:30 — Мария С. | пр. Мира 12

(или «Заказов на сегодня нет»)
━━━━━━━━━━━━━━━
```

Клавиатура:
```python
[
    [InlineKeyboardButton("📦 Заказы", callback_data="orders"),
     InlineKeyboardButton("👥 Клиенты", callback_data="clients")],
    [InlineKeyboardButton("📢 Маркетинг", callback_data="marketing"),
     InlineKeyboardButton("📊 Отчёты", callback_data="reports")],
    [InlineKeyboardButton("⚙️ Настройки", callback_data="settings")],
]
```

#### Раздел «Заказы»

**Экран заказов** (`callback: orders`):
- Список заказов на сегодня (те же данные что на Home, но кликабельные кнопки)
- Каждый заказ — отдельная кнопка: `"10:00 — Иван П. | Уборка"` → callback `orders:view:N`
- Кнопки внизу: `[+ Новый заказ]`, `[📅 Другой день]`, `[🏠 Главная]`

**Карточка заказа** (`callback: orders:view:N`):
```
📋 Заказ #{id}
━━━━━━━━━━━━━━━
👤 {имя клиента}
📞 {телефон}
📍 {адрес}
🕐 {время} | {дата}
🛠 {услуги через запятую}
💰 Итого: {сумма} ₽
📊 Статус: {статус}
━━━━━━━━━━━━━━━
```
Кнопки (если статус `new` или `confirmed`):
```
[✅ Провести]  [📅 Перенести]
[❌ Отменить]  [◀️ Назад]
```
Если статус `done/cancelled/moved` — только `[◀️ Назад]`

**Инлайн-календарь** (`callback: orders:calendar` и `orders:calendar:YYYY:M`):
Генерирует сетку месяца как inline-кнопки.
- Заголовок: `◀️  Март 2026  ▶️`
- Каждый день — кнопка с датой: callback `orders:calendar:date:2026-03-15`
- Дни с заказами — помечены звёздочкой в тексте кнопки: `"15*"`
- Прошлые дни доступны
- `◀️` и `▶️` листают месяц: callback `orders:calendar:2026:2` (февраль)

При выборе даты (`orders:calendar:date:YYYY-MM-DD`) → показывает экран заказов за эту дату.

**Заглушки для FSM:**
- `orders:new` → сообщение «🚧 Создание заказа — в разработке» + `[◀️ Назад]`
- `orders:complete:N` → заглушка
- `orders:move:N` → заглушка
- `orders:cancel:N` → заглушка

#### Раздел «Клиенты»

**Экран клиентов** (`callback: clients`):
```
👥 Клиенты
━━━━━━━━━━━━━━━
Введите имя или телефон для поиска:
```
Кнопки: `[+ Добавить клиента]`, `[🏠 Главная]`

Поиск — через обычное текстовое сообщение (не FSM, просто обработчик текста когда активен экран клиентов). После ввода — редактируем Home-сообщение, добавляем результаты кнопками.

Храни в FSM context текущий активный экран (`current_screen: "clients"`), чтобы знать куда направить текстовый ввод.

**Карточка клиента** (`callback: clients:view:N`):
```
👤 {имя}
📞 {телефон}
🎂 {дата рождения или «не указана»}
💰 Бонусов: {баланс} ₽
🛒 Заказов: {кол-во} | Потрачено: {сумма} ₽
📝 {заметка или «—»}
━━━━━━━━━━━━━━━
```
Кнопки:
```
[📋 История]  [🎁 Бонусы]
[✏️ Изменить] [📝 Заметка]
[◀️ Назад]
```

**История клиента** (`callback: clients:history:N`):
Список последних 20 заказов, каждый строкой. Кнопка `[◀️ Назад]`.

**Бонусы клиента** (`callback: clients:bonus:N`):
Баланс + последние 20 записей лога. Кнопки `[➕ Начислить]  [➖ Списать]  [◀️ Назад]`.
Начислить/Списать → заглушки.

**Заглушки:**
- `clients:new` → заглушка
- `clients:edit:N` → заглушка
- `clients:note:N` → заглушка

#### Раздел «Маркетинг»

**Экран маркетинга** (`callback: marketing`):
```
📢 Маркетинг
━━━━━━━━━━━━━━━
```
Кнопки: `[📨 Рассылка]`, `[🎁 Создать акцию]`, `[🏠 Главная]`

Оба пункта → заглушки.

#### Раздел «Отчёты»

**Экран отчётов** (`callback: reports`, по умолчанию текущий месяц):

Функция `get_reports_data(master_id, date_from, date_to)` → считает из БД:
- выручку
- кол-во заказов
- новых клиентов
- повторных
- средний чек
- всего в базе
- топ-5 услуг

```
📊 Отчёты — {период}
━━━━━━━━━━━━━━━
💰 Выручка: {сумма} ₽
🛒 Заказов: {кол-во}
👥 Новых клиентов: {кол-во}
🔄 Повторных: {кол-во}
🧾 Средний чек: {сумма} ₽
📋 Всего в базе: {кол-во}
━━━━━━━━━━━━━━━
Топ услуг:
• {услуга} — {сумма} ₽
...
━━━━━━━━━━━━━━━
```
Кнопки фильтров (активный период — помечен `·` перед текстом):
```
[· Месяц]  [Сегодня]  [Неделя]  [📅 Период]
[🏠 Главная]
```

`reports:today`, `reports:week`, `reports:month` → обновляют тот же экран с новыми данными.
`reports:period` → заглушка (FSM ввода дат — следующий этап).

#### Раздел «Настройки»

**Экран настроек** (`callback: settings`):
Кнопки: `[👤 Профиль]`, `[🎁 Бонусная программа]`, `[🛠 Справочник услуг]`, `[🔗 Инвайт-ссылка]`, `[🏠 Главная]`

**Профиль** (`callback: settings:profile`):
Показывает текущие данные мастера. Кнопки для каждого поля → заглушки. `[◀️ Назад]`.

**Бонусная программа** (`callback: settings:bonus`):
Показывает текущие настройки. Кнопки изменения → заглушки. `[◀️ Назад]`.

**Справочник услуг** (`callback: settings:services`):
Список услуг мастера кнопками. `[+ Добавить услугу]` → заглушка. `[◀️ Назад]`.

**Инвайт-ссылка** (`callback: settings:invite`):
Показывает ссылку `t.me/{CLIENT_BOT_USERNAME}?start={invite_token}`.
Кнопка `[🖼 QR-код]` → заглушка. `[◀️ Назад]`.

---

### client_bot.py

Та же концепция: Home — постоянное сообщение (хранить `home_message_id` в `master_clients`).

#### Home клиента

```
👋 Привет, {имя}!

💰 Ваши бонусы: {баланс} ₽
Мастер: {имя мастера}
━━━━━━━━━━━━━━━
```
Клавиатура:
```python
[
    [InlineKeyboardButton("💰 Мои бонусы", callback_data="bonuses"),
     InlineKeyboardButton("📋 История", callback_data="history")],
    [InlineKeyboardButton("🎁 Акции", callback_data="promos"),
     InlineKeyboardButton("📞 Заказать", callback_data="order_request")],
    [InlineKeyboardButton("❓ Вопрос", callback_data="question"),
     InlineKeyboardButton("📸 Фото/видео", callback_data="media")],
    [InlineKeyboardButton("👨‍🔧 Мой мастер", callback_data="master_info"),
     InlineKeyboardButton("🔔 Уведомления", callback_data="notifications")],
]
```

#### Разделы client_bot

**💰 Мои бонусы** (`bonuses`): баланс + лог последних 10 операций. `[🏠 Главная]`.

**📋 История** (`history`): список последних 20 заказов. `[🏠 Главная]`.

**🎁 Акции** (`promos`): список активных акций мастера. `[🏠 Главная]`.

**👨‍🔧 Мой мастер** (`master_info`): профиль мастера (имя, сфера, контакты, соцсети, режим работы). `[🏠 Главная]`.

**🔔 Уведомления** (`notifications`): переключатели из `master_clients`. Нажатие → toggle в БД → обновить сообщение. `[🏠 Главная]`.

**📞 Заказать**, **❓ Вопрос**, **📸 Фото/видео** → заглушки (FSM — следующий этап).

---

## keyboards.py — обновить

Все функции-генераторы клавиатур вынести в `keyboards.py`:

```python
def home_master_kb() -> InlineKeyboardMarkup: ...
def orders_kb(orders: list) -> InlineKeyboardMarkup: ...
def order_card_kb(order_id: int, can_act: bool) -> InlineKeyboardMarkup: ...
def calendar_kb(year: int, month: int, active_dates: list[date]) -> InlineKeyboardMarkup: ...
def clients_kb(results: list | None = None) -> InlineKeyboardMarkup: ...
def client_card_kb(client_id: int) -> InlineKeyboardMarkup: ...
def client_history_kb(client_id: int) -> InlineKeyboardMarkup: ...
def client_bonus_kb(client_id: int) -> InlineKeyboardMarkup: ...
def marketing_kb() -> InlineKeyboardMarkup: ...
def reports_kb(active: str = "month") -> InlineKeyboardMarkup: ...
def settings_kb() -> InlineKeyboardMarkup: ...
def settings_profile_kb() -> InlineKeyboardMarkup: ...
def settings_bonus_kb() -> InlineKeyboardMarkup: ...
def settings_services_kb(services: list) -> InlineKeyboardMarkup: ...
def settings_invite_kb() -> InlineKeyboardMarkup: ...
def home_client_kb() -> InlineKeyboardMarkup: ...
def back_home_kb() -> InlineKeyboardMarkup: ...  # только [◀️ Назад] и [🏠 Главная]
def stub_kb(back_callback: str) -> InlineKeyboardMarkup: ...  # заглушка: [◀️ Назад]
```

---

## database.py — добавить функции

```python
# Заказы
async def get_orders_today(master_id: int) -> list[Order]: ...
async def get_orders_by_date(master_id: int, date: date) -> list[Order]: ...
async def get_order_by_id(order_id: int, master_id: int) -> Order | None: ...
async def get_active_dates(master_id: int, year: int, month: int) -> list[date]: ...

# Клиенты
async def search_clients(master_id: int, query: str) -> list[Client]: ...
async def get_client_with_stats(master_id: int, client_id: int) -> dict: ...
async def get_client_orders(master_id: int, client_id: int, limit: int = 20) -> list[Order]: ...
async def get_client_bonus_log(master_id: int, client_id: int, limit: int = 20) -> list[BonusLogEntry]: ...

# Отчёты
async def get_reports(master_id: int, date_from: date, date_to: date) -> dict: ...

# Акции
async def get_active_campaigns(master_id: int) -> list[Campaign]: ...

# Home message id
async def save_master_home_message_id(master_id: int, message_id: int): ...
async def save_client_home_message_id(master_id: int, client_id: int, message_id: int): ...

# Уведомления клиента
async def toggle_client_notification(master_id: int, client_id: int, field: str) -> bool: ...
```

---

## Критерии проверки

1. `/start` в master_bot → Home отображается и редактируется при навигации (не создаёт новые сообщения)
2. Все 5 кнопок главного меню → открывают соответствующие разделы
3. Раздел «Заказы» → календарь работает, листается по месяцам, заглушки для действий
4. Раздел «Клиенты» → поиск по тексту работает (ищет в БД), карточка открывается
5. Раздел «Отчёты» → показывает данные, переключение периодов работает
6. Все кнопки «◀️ Назад» и «🏠 Главная» работают корректно
7. `/start` в client_bot → Home клиента с балансом, все 8 кнопок работают (или заглушки)
8. Кнопка «🔔 Уведомления» → реально переключает и сохраняет в БД
9. Нет необработанных callback_query (все колбэки имеют обработчик)
10. При удалении Home-сообщения пользователем — бот создаёт новое без ошибки
