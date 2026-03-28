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
│       │   ├── Home.jsx           — баланс, ближайшая запись, лог бонусов
│       │   ├── Booking.jsx        — выбор услуги, MainButton, экран успеха
│       │   ├── Bonuses.jsx        — 2 вкладки: лог бонусов / история заказов
│       │   └── Promos.jsx         — карточки акций, empty state
│       ├── components/
│       │   ├── BottomNav.jsx      — 4 вкладки с inline SVG иконками + haptic
│       │   ├── Skeleton.jsx       — пульсирующий placeholder (skeleton-pulse)
│       │   └── ErrorScreen.jsx    — экран ошибки + кнопка retry
│       └── master/                — мастерский интерфейс
│           ├── MasterApp.jsx      — корневой компонент мастера, таб-навигация
│           ├── pages/
│           │   ├── Dashboard.jsx  — сводка дня, статистика, кнопка создания заказа
│           │   ├── Calendar.jsx   — WeekStrip + список заказов на выбранный день
│           │   ├── OrderDetail.jsx — карточка заказа, проведение/перенос/отмена
│           │   ├── OrderCreate.jsx — 4-шаговое создание заказа (клиент, услуги, дата, подтверждение)
│           │   ├── Broadcast.jsx  — 3-шаговая рассылка (сегмент, текст, отправка)
│           │   └── More.jsx       — профиль мастера, инвайт-ссылка, поддержка
│           ├── components/
│           │   ├── MasterNav.jsx  — нижняя навигация (4 таба)
│           │   ├── WeekStrip.jsx  — горизонтальная лента дней недели
│           │   ├── DaySchedule.jsx — список заказов дня
│           │   ├── OrderCard.jsx  — карточка заказа в списке
│           │   └── StatCard.jsx   — карточка статистики
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
    │       ├── client.py          — GET /api/me
    │       ├── orders.py          — GET /api/orders, POST /api/orders/request
    │       ├── bonuses.py         — GET /api/bonuses
    │       ├── promos.py          — GET /api/promos
    │       ├── services.py        — GET /api/services
    │       └── master/            — API для мастера
    │           ├── dashboard.py   — GET /api/master/me, /api/master/dashboard, /api/master/invite-link
    │           ├── calendar.py    — GET /api/master/orders/dates
    │           ├── orders.py      — CRUD заказов мастера
    │           ├── clients.py     — GET /api/master/clients, /api/master/clients/{id}/last-address
    │           ├── services_router.py — GET /api/master/services
    │           └── broadcast.py   — POST /api/master/broadcast/preview, /send, /segments
    │
    └── handlers/                  — обработчики master_bot по разделам
        ├── __init__.py
        ├── common.py              — общие хендлеры (home, навигация)
        ├── registration.py        — регистрация мастера
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
| `masters` | Мастера: профиль, настройки бонусов, GC credentials |
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

## UI паттерны (боты)

- **Гибридный UI:** Home — постоянное сообщение, редактируется. FSM-сценарии — новые сообщения, удаляются после завершения.
- **Callback data формат:** `раздел:действие:параметр` (например `orders:view:12`)
- **Навигация:** везде есть `[◀️ Назад]` и `[🏠 Главная]`
- **Reply-кнопка** `[🏠 Домой]` — постоянно видна, прерывает любой FSM

---

## Текущее состояние разработки

### Реализовано ✅
- **Mini App бэкенд (клиентский)** — FastAPI (`src/api/`), эндпоинты `/api/me`, `/api/orders`, `/api/bonuses`, `/api/promos`, `/api/services`, `/api/orders/request`. Авторизация через Telegram initData (HMAC-SHA256). Dev bypass через `APP_ENV=development`.
- **Mini App фронтенд (клиентский)** — React 19 + Vite (`miniapp/`), 4 экрана, Telegram WebApp API, адаптивная тема.
- **Master Mini App** — полный мастерский интерфейс (`miniapp/src/master/`):
  - Dashboard — сводка дня, статистика (неделя/месяц), ближайшие заказы
  - Calendar — WeekStrip + список заказов на выбранный день
  - OrderDetail — карточка заказа, провести / перенести / отменить с bottom sheet
  - OrderCreate — 4-шаговое создание заказа (поиск клиента, услуги, дата/время, подтверждение)
  - Broadcast — 3-шаговая рассылка (сегмент, текст, предпросмотр и отправка)
  - More — профиль мастера, инвайт-ссылка, поддержка
  - Telegram BackButton на всех nested экранах (хук `useBackButton`)
- **Master Mini App бэкенд** — `src/api/routers/master/`: dashboard, calendar, orders (CRUD), clients, services, broadcast, invite-link
- Регистрация мастера и клиента (по инвайт-ссылке)
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
- **Mini App деплой** — сборка `miniapp/dist/` и раздача через nginx на `app.crmfit.ru`

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
