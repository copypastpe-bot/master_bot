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
| API для Mini App | FastAPI + uvicorn (порт 8081, в разработке) |
| Фронт Mini App | React + Vite (в разработке) |
| Деплой | VPS, nginx, Docker |

---

## Структура проекта

```
master-bot/
├── main.py                        — точка входа, asyncio.gather() всех компонентов
├── run_master.py                  — запуск только master_bot
├── run_client.py                  — запуск только client_bot
├── requirements.txt
├── .env                           — секреты (не коммитить)
├── .env.example                   — шаблон переменных
│
└── src/
    ├── config.py                  — загрузка .env (токены, DATABASE_URL, порты)
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

`main.py` запускает параллельно: master_bot + client_bot + oauth_server (8080).

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
- **Mini App** — FastAPI бэкенд (`src/api/`) + React фронт (`miniapp/`)

### Запланировано 📋
- UI заказов с листанием по неделям и инлайн-календарём везде
- Список клиентов с пагинацией по алфавиту
- Массовое начисление бонусов с ограниченным сроком
- Сгорание бонусов через год

---

## Правила кода

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

---

## Важные предупреждения

- `keyboards.py` — большой файл, читать внимательно перед правками
- `home_message_id` хранится в БД — при редактировании Home использовать `edit_message_text`, не `send_message`
- Уведомления клиентам отправлять через `client_bot` instance, не через `master_bot`
- GC интеграция опциональна — все действия с заказами работают если GC не подключён
- `crypto.py` — не менять без понимания последствий для зашифрованных данных в БД
