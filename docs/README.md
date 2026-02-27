# Master CRM Bot

Telegram-сервис для частных мастеров: учёт клиентов, заказов и программа лояльности.

## Структура проекта

```
master-crm-bot/
├── master_bot.py          # Бот для мастеров
├── client_bot.py          # Бот для клиентов
├── database.py            # Слой работы с БД
├── models.py              # Модели данных
├── scheduler.py           # Фоновые задачи
├── google_calendar.py     # Интеграция Google Calendar
├── notifications.py       # Отправка уведомлений
├── keyboards.py           # Inline-клавиатуры
├── states.py              # FSM состояния
├── config.py              # Конфигурация
├── utils.py               # Утилиты
├── migrations/            # SQL миграции
├── .env.example
├── requirements.txt
├── SPEC.md                # Полная спецификация
└── README.md
```

## Быстрый старт (dev)

```bash
# 1. Клонировать репозиторий
git clone <repo_url>
cd master-crm-bot

# 2. Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Настроить .env
cp .env.example .env
# Заполнить токены ботов и остальные переменные

# 5. Применить миграции
python -c "from database import init_db; import asyncio; asyncio.run(init_db())"

# 6. Запустить ботов (два отдельных терминала)
python master_bot.py
python client_bot.py
```

## Переменные окружения

| Переменная | Описание |
|---|---|
| `MASTER_BOT_TOKEN` | Токен master_bot от @BotFather |
| `CLIENT_BOT_TOKEN` | Токен client_bot от @BotFather |
| `CLIENT_BOT_USERNAME` | Username client_bot (без @) |
| `DATABASE_URL` | SQLite: `sqlite:///db.sqlite3` / PostgreSQL: `postgresql://...` |
| `GOOGLE_CREDENTIALS_PATH` | Путь к JSON-ключу Google API |
| `LOG_LEVEL` | DEBUG / INFO / WARNING (по умолчанию INFO) |

## Деплой на VPS (prod)

```bash
# Установить PostgreSQL, создать БД
# Настроить .env с PostgreSQL URL
# Создать два systemd-сервиса: master-bot.service и client-bot.service
```

Подробнее см. SPEC.md
