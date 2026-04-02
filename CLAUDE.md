# CLAUDE.md — Master Bot

## О проекте

**Master Bot** — SaaS-система для частных мастеров (клинеры, сантехники, парикмахеры и др.).
Два Telegram-бота на одной базе данных:
- `master_bot` — для мастера: клиенты, заказы, бонусы, маркетинг, отчёты
- `client_bot` — для клиентов мастера: бонусы, история, акции, заявки

Сайт: `https://crmfit.ru`

---

## Стек

| Компонент | Технология |
|---|---|
| Боты | Python 3.11, aiogram 3.x |
| БД | SQLite (aiosqlite), PostgreSQL планируется |
| Планировщик | APScheduler |
| OAuth сервер | aiohttp (порт 8090) |
| API для Mini App | FastAPI + uvicorn (порт 8081) |
| Фронт Mini App | React 19 + Vite 8, @twa-dev/sdk, React Query, axios |
| Деплой | VPS `75.119.153.118`, nginx, Docker Compose |

---

## Структура проекта

```
master-bot/
├── main.py                        — точка входа, asyncio.gather() всех компонентов
├── run_master.py                  — master_bot + API сервер (порт 8081) + oauth (порт 8090)
├── run_client.py                  — запуск только client_bot
├── requirements.txt
├── .env                           — секреты (не коммитить)
├── .env.example                   — шаблон переменных
├── docker-compose.yml             — два контейнера: master_bot, client_bot
│
├── miniapp/                       — Telegram Mini App (React + Vite)
│   ├── index.html
│   ├── vite.config.js             — proxy /api → localhost:8081, port 5173
│   ├── package.json
│   ├── .env.development           — VITE_API_URL=http://localhost:8081
│   ├── .env.production            — VITE_API_URL=https://api.crmfit.ru
│   └── src/
│       ├── main.jsx               — QueryClient + WebApp.ready() + WebApp.expand()
│       ├── App.jsx                — useState роутинг + Telegram BackButton
│       ├── theme.css              — CSS переменные из Telegram темы
│       ├── api/
│       │   └── client.js          — axios instance, dev bypass, все запросы
│       ├── pages/
│       │   ├── Home.jsx           — баланс, ближайшая запись, лог бонусов; bottom sheet выбора мастера (мультимастер)
│       │   ├── Booking.jsx        — выбор услуги, MainButton, экран успеха
│       │   ├── Bonuses.jsx        — 2 вкладки: лог бонусов / история заказов
│       │   ├── Promos.jsx         — карточки акций, empty state
│       │   └── MasterSelectScreen.jsx — экран выбора мастера при 2+ мастерах (показывается до перехода в ClientApp)
│       ├── components/
│       │   ├── BottomNav.jsx      — 4 вкладки с inline SVG иконками + haptic
│       │   ├── Skeleton.jsx       — пульсирующий placeholder (skeleton-pulse)
│       │   └── ErrorScreen.jsx    — экран ошибки + кнопка retry
│       └── master/                — мастерский интерфейс
│           ├── MasterApp.jsx      — корневой компонент мастера, таб-навигация
│           ├── pages/
│           │   ├── Dashboard.jsx  — сводка дня, статистика (для новых мастеров — мотивационный блок вместо KPI), кнопка создания заказа, онбординг-баннер
│           │   ├── Calendar.jsx   — WeekStrip + список заказов на выбранный день
│           │   ├── OrderDetail.jsx — карточка заказа, проведение/перенос/отмена
│           │   ├── OrderCreate.jsx — 4-шаговое создание заказа (клиент, услуги, дата, подтверждение)
│           │   ├── Broadcast.jsx  — 4-шаговая рассылка (текст, медиа, сегмент, отправка); empty state при 0 клиентов с TG (инвайт-ссылка)
│           │   ├── Reports.jsx    — аналитика: выручка, заказы, клиенты, график
│           │   ├── ClientsList.jsx — список клиентов с поиском и пагинацией
│           │   ├── ClientCard.jsx — карточка клиента: история, бонусы, редактирование
│           │   ├── More.jsx       — профиль мастера, инвайт-ссылка, поддержка
│           │   └── MasterOnboarding.jsx — 4-шаговый онбординг нового мастера (имя → ниша-чипсы → первый клиент+запись → финал); шаг 3 можно пропустить
│           ├── components/
│           │   ├── MasterNav.jsx  — нижняя навигация: Главная / Календарь / Рассылки (иконка конверт MailIcon) / Другое
│           │   ├── WeekStrip.jsx  — горизонтальная лента дней недели
│           │   ├── DaySchedule.jsx — список заказов дня
│           │   ├── OrderCard.jsx  — карточка заказа в списке
│           │   ├── StatCard.jsx   — карточка статистики
│           │   └── ClientAddSheet.jsx — bottom sheet добавления нового клиента
│           └── hooks/
│               └── useBackButton.js — хук для Telegram BackButton на nested экранах
│
└── src/
    ├── config.py                  — загрузка .env (токены, DATABASE_URL, порты, APP_ENV)
    ├── database.py                — все функции БД (aiosqlite)
    ├── models.py                  — dataclasses: Master, Client, MasterClient, Service, Order, BonusLog, Campaign
    ├── states.py                  — FSM стейты (aiogram)
    ├── keyboards.py               — все inline и reply клавиатуры
    ├── notifications.py           — уведомления клиентам через client_bot
    ├── utils.py                   — format_phone, parse_date, generate_invite_token
    ├── crypto.py                  — шифрование/хеширование
    ├── google_calendar.py         — Google Calendar OAuth + CRUD событий
    ├── oauth_server.py            — aiohttp сервер порт 8090 (OAuth callback от Google)
    ├── scheduler.py               — APScheduler (напоминания, бонусы на ДР)
    │
    ├── master_bot.py              — точка входа master_bot, регистрация роутеров
    ├── client_bot.py              — клиентский бот (полностью)
    │
    ├── api/                       — FastAPI бэкенд для Mini App
    │   ├── app.py                 — FastAPI app, CORS (app.crmfit.ru, localhost:5173)
    │   ├── auth.py                — валидация Telegram initData (HMAC-SHA256)
    │   ├── dependencies.py        — get_current_client + get_current_master + dev bypass
    │   └── routers/
    │       ├── client.py          — GET /api/me (поддерживает ?master_id для мультимастера)
    │       ├── orders.py          — GET /api/orders (поддерживает ?master_id), POST /api/orders/request
    │       ├── bonuses.py         — GET /api/bonuses (поддерживает ?master_id)
    │       ├── promos.py          — GET /api/promos (поддерживает ?master_id)
    │       ├── services.py        — GET /api/services (поддерживает ?master_id)
    │       ├── auth_router.py     — GET /api/auth/role → {role: master|client|unknown}
    │       ├── client_masters.py  — GET /api/client/masters, POST /api/client/link
    │       └── master/            — API для мастера
    │           ├── auth.py        — POST /api/master/register (без dev-bypass, требует реальный initData)
│           ├── dashboard.py   — GET /api/master/me, /api/master/dashboard (+ total_done_orders, onboarding_banner), /api/master/invite-link
    │           ├── calendar.py    — GET /api/master/orders/dates
    │           ├── orders.py      — CRUD заказов мастера
    │           ├── clients.py     — GET /api/master/clients, /api/master/clients/{id}/last-address
    │           ├── services_router.py — GET /api/master/services
    │           ├── broadcast.py   — GET /can-send; GET /segments; POST /preview (JSON), /send (multipart/form-data с опциональным UploadFile)
│           └── reports.py     — GET /api/master/reports (параметры: period или date_from/date_to)
    │
    └── handlers/                  — обработчики master_bot по разделам
        ├── __init__.py
        ├── common.py              — /start → фото-баннер + кнопка Mini App (FSM регистрации отключён)
        ├── registration.py        — FSM регистрации (отключён, код закомментирован)
        ├── orders.py              — заказы (создание, проведение, перенос, отмена)
        ├── clients.py             — блок клиентов (карточка, история, бонусы)
        ├── marketing.py           — рассылки и акции
        ├── reports.py             — отчёты
        └── settings.py            — настройки (профиль, бонусы, услуги, GC)
```

---

## Как запустить (dev)

```bash
# Установить зависимости
pip install -r requirements.txt

# Создать .env из шаблона и заполнить токены
cp .env.example .env

# Запустить оба бота + сервисы
python main.py

# Или по отдельности
python run_master.py
python run_client.py
```

`run_master.py` запускает параллельно: master_bot + API сервер (8081) + oauth_server (8090).

### Mini App (фронтенд)

```bash
cd miniapp
npm install
npm run dev      # http://localhost:5173 (proxy /api → :8081)
npm run build    # сборка в miniapp/dist/
```

**Dev bypass:** без реального Telegram запускать с `APP_ENV=development` на бэкенде — тогда `X-Init-Data: "dev"` принимается без HMAC. В браузере автоматически подставляется dev-режим.

### Деплой на сервер

```bash
ssh deploy@75.119.153.118
cd /opt/master_bot
git pull
docker compose down && docker compose up -d --build
```

Контейнеры: `master_bot` (порты 8081, 8090), `client_bot`.

---

## Переменные окружения (.env)

```
MASTER_BOT_TOKEN=        — токен master_bot от BotFather
CLIENT_BOT_TOKEN=        — токен client_bot от BotFather
CLIENT_BOT_USERNAME=     — username client_bot без @
DATABASE_URL=sqlite:///db.sqlite3
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=https://crmfit.ru/oauth/callback
OAUTH_SERVER_PORT=8090
API_PORT=8081
MINIAPP_URL=https://app.crmfit.ru
LOG_LEVEL=INFO
APP_ENV=production           — development включает dev bypass в API (X-Init-Data: "dev")
```

---

## База данных

**Паттерн работы:** каждая функция в `database.py` сама открывает и закрывает соединение через `get_connection()`. Пул не используется.

**Основные таблицы:**

| Таблица | Назначение |
|---|---|
| `masters` | Мастера: профиль, настройки бонусов, GC credentials, `onboarding_skipped_first_client`, `onboarding_banner_shown` |
| `clients` | Клиенты: tg_id, имя, телефон, ДР |
| `master_clients` | Связка мастер↔клиент: баланс бонусов, настройки уведомлений |
| `orders` | Заказы: статус, время, сумма, оплата, бонусы |
| `order_items` | Услуги в заказе |
| `bonus_log` | Лог бонусных операций |
| `services` | Справочник услуг мастера |
| `campaigns` | Рассылки и акции |
| `inbound_requests` | Заявки от клиентов (вопрос, заказ, медиа) |

**Жизненный цикл заказа:**
`new` → `confirmed` → `done` / `moved` / `cancelled`

---

## UI паттерны

### Бот (master_bot)
- `/start` и `/home` — только фото-баннер + кнопка "Открыть приложение →" (WebApp кнопка)
- FSM регистрации отключён — весь онбординг в Mini App
- Оставшиеся FSM-хендлеры: настройки профиля, бонусы, услуги, GC — в `handlers/`

### Mini App (мастерский)
- **Навигация:** таб-бар — Главная / Календарь / Рассылки (конверт) / Другое
- **Nested screens:** `navStack` в `MasterApp.jsx`; Telegram BackButton через `useBackButton`
- **Dashboard empty states:** новый мастер (0 done-заказов) видит 📊-блок вместо KPI и "Пока записей нет" вместо расписания

---

## Текущее состояние разработки

### Реализовано ✅
- **Mini App бэкенд (клиентский)** — FastAPI (`src/api/`), эндпоинты `/api/me`, `/api/orders`, `/api/bonuses`, `/api/promos`, `/api/services`, `/api/orders/request`. Авторизация через Telegram initData (HMAC-SHA256). Dev bypass через `APP_ENV=development`.
- **Mini App фронтенд (клиентский)** — React 19 + Vite (`miniapp/`), 4 экрана, Telegram WebApp API, адаптивная тема.
- **Master Mini App** — полный мастерский интерфейс (`miniapp/src/master/`):
  - Dashboard — сводка дня; для новых мастеров (0 done-заказов): мотивационный блок 📊 вместо KPI, empty states в расписании с кнопкой "Добавить первую запись"; онбординг-баннер если пропустил шаг 3
  - Calendar — WeekStrip + список заказов на выбранный день
  - OrderDetail — карточка заказа, провести / перенести / отменить с bottom sheet
  - OrderCreate — 4-шаговое создание заказа (поиск клиента, услуги, дата/время, подтверждение)
  - Broadcast — 4-шаговая рассылка (текст, медиа фото/видео, сегмент, предпросмотр и отправка); при 0 клиентов с TG — empty state с инвайт-ссылкой; `/send` принимает `multipart/form-data`
  - Reports (Аналитика) — выручка, заказы, новые клиенты, топ услуг, график по дням; доступ через клики на StatCard Dashboard
  - ClientsList — список клиентов с поиском и бесконечной прокруткой
  - ClientCard — карточка клиента: история заказов, бонусы, редактирование
  - ClientAddSheet — bottom sheet добавления клиента; обрабатывает 409 (дубликат, архивный)
  - More — профиль мастера, инвайт-ссылка, поддержка
  - Telegram BackButton на всех nested экранах (хук `useBackButton`)
- **Master Mini App бэкенд** — `src/api/routers/master/`: dashboard (+ total_done_orders, onboarding_banner), calendar, orders (CRUD), clients (GET list + POST create), services, broadcast (+ GET /can-send), reports, invite-link; регистрация в `auth.py`
- **Empty states для новых мастеров** — Dashboard: мотивационный блок 📊, "Пока записей нет" + кнопка первой записи, онбординг-баннер; Рассылки: экран с инвайт-ссылкой при 0 клиентов с TG
- **Навигация** — вкладка "Рассылки" с иконкой конверта (MailIcon) вместо рупора (MegaphoneIcon)
- **Регистрация мастера** — только через Mini App:
  - `master_bot /start` → фото-баннер + кнопка "Открыть приложение →" (FSM регистрации удалён)
  - Mini App: `GET /api/auth/role` → `unknown` → `MasterOnboarding.jsx` (4 шага: имя → ниша → первый клиент/пропустить → финал) → POST `/api/master/register` → `onRegistered()` → `MasterApp`
  - Путь "Пропустить" (шаг 3): `PUT /api/master/profile { onboarding_skipped_first_client: true }` → Dashboard показывает баннер "Добавь первого клиента..."
  - Баннер скрывается через `PUT /api/master/profile { onboarding_banner_shown: true }`
  - 12 ниш + "Другое": Клининг, Химчистка, Парикмахер, Маникюр, Груминг, Массаж, Ремонт бытовой техники, Мастер на час, Репетитор, Фотограф, Психолог, Садовник, Другое
- **Мультимастерность (подход C)** — клиент может быть привязан к нескольким мастерам:
  - Привязка через бот: `/start {invite_token}` → `link_existing_client_to_master` + `_active_masters[tg_id]`
  - Привязка через Mini App: `start_param=invite_TOKEN` → POST `/api/client/link` с `{invite_token}` → обновление списка
  - Выбор мастера в Mini App: `MasterSelectScreen` (при 2+ мастерах на старте) + bottom sheet в Home
  - Выбор мастера в боте: inline-кнопки `select_master:{id}` + `_active_masters` dict в памяти
  - Все клиентские API принимают опциональный `?master_id`; `_activeMasterId` в `client.js` передаётся в каждый запрос
  - `get_client_context(tg_id, master_id)`: если `master_id` задан — используется, иначе — последний посещённый (ORDER BY last_visit DESC)
- Регистрация клиента (по инвайт-ссылке через бот)
- Полный цикл заказов: создание, проведение, перенос, отмена
- Клиентская база: карточка, история, бонусы, заметки, редактирование
- Бонусная программа: начисление, списание, ручные операции
- Напоминания: за 24ч (с подтверждением клиента) и за 1ч, бонус на ДР
- Маркетинг: рассылки по сегментам с медиа, акции
- Отчёты: выручка, заказы, клиенты, топ услуг, произвольный период
- Настройки: профиль, бонусная программа, справочник услуг, инвайт QR
- Google Calendar: OAuth + создание/обновление/удаление событий
- client_bot: бонусы, история, акции, заявка, вопрос, фото/видео
- Планировщик: напоминания, бонусы на день рождения
- Рефакторинг: master_bot разбит на handlers/

### В разработке 🔄
- Нет активных задач

### Запланировано 📋
- Список клиентов с пагинацией по алфавиту
- Массовое начисление бонусов с ограниченным сроком
- Сгорание бонусов через год

---

## Git workflow

Разработчик работает один. Всегда работать в ветке `main` напрямую — не создавать feature-ветки и worktree. Скиллы `superpowers:using-git-worktrees` не применять.

### Деплой бэкенда (бот + API)

```bash
git push origin main
ssh deploy@75.119.153.118 "cd /opt/master_bot && git pull origin main --ff-only && docker compose up -d --build master_bot"
```

Сервер никогда не делает `git commit` или `git merge` — только `git pull`.

### Деплой Mini App (фронтенд)

Нужен при любых изменениях в `miniapp/src/` или `miniapp/package.json`:

```bash
bash deploy_miniapp.sh
```

Скрипт делает всё сам: `npm run build` → `rsync dist/` на сервер → обновляет nginx конфиг → `nginx reload`.

После деплоя nginx выводит `warn` про `protocol options redefined` — это норма (конфликт с n8n конфигом), главное что в конце `syntax ok` и `test is successful`.

### Когда деплоить что

| Изменения в | Деплой |
|---|---|
| `src/`, `migrations/`, `requirements.txt` | только бэкенд |
| `miniapp/src/`, `miniapp/package.json` | только Mini App |
| И то и другое | оба деплоя |

---

## Правила кода

### Backend (Python)
- Весь код — async/await
- Импорты из `src.*` (не относительные)
- Новые обработчики master_bot — только в `src/handlers/` в соответствующий файл
- Новые функции БД — только в `src/database.py`
- Новые клавиатуры — только в `src/keyboards.py`
- Новые FSM стейты — только в `src/states.py`
- Тексты уведомлений — в `src/notifications.py`
- Не дублировать логику между master_bot и client_bot — выносить в общие модули
- При изменении схемы БД — добавлять новый файл миграции в `migrations/`
- Не трогать `.env` — только `.env.example`

### Frontend (Mini App)
- Новые страницы — в `miniapp/src/pages/`
- Новые компоненты — в `miniapp/src/components/`
- Все запросы к API — только через `miniapp/src/api/client.js`
- Стили — только через CSS переменные `var(--tg-*)`, не хардкодить цвета
- Haptic feedback при любом нажатии: `WebApp.HapticFeedback.impactOccurred('light')`
- Всегда проверять наличие WebApp API: `typeof WebApp?.SomeApi?.method === 'function'`
- После изменений: `npm run build` в `miniapp/` должен проходить без ошибок

---

## Важные предупреждения

- `keyboards.py` — большой файл, читать внимательно перед правками
- `home_message_id` хранится в БД — при редактировании Home использовать `edit_message_text`, не `send_message`
- Уведомления клиентам отправлять через `client_bot` instance, не через `master_bot`
- GC интеграция опциональна — все действия с заказами работают если GC не подключён
- `crypto.py` — не менять без понимания последствий для зашифрованных данных в БД
