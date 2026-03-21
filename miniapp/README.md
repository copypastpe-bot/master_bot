# Mini App — CRM Fit

Telegram Mini App для клиентов мастера. Работает внутри Telegram через кнопку "📱 Открыть приложение" или Menu Button.

## Стек

| Компонент | Технология |
|---|---|
| Фреймворк | React 19 + Vite 8 |
| Данные | @tanstack/react-query |
| Telegram SDK | @twa-dev/sdk |
| HTTP | axios |
| Роутинг | useState (без react-router) |

## Страницы

| Страница | URL-путь | Описание |
|---|---|---|
| Главная | `/` (page=home) | Баланс бонусов, ближайший заказ, последние операции |
| Запись | page=booking | Выбор услуги + комментарий, отправка заявки |
| Бонусы | page=bonuses | Баланс + история операций + история заказов |
| Акции | page=promos | Карточки активных акций мастера |

## Локальная разработка

```bash
cd miniapp

# Установить зависимости
npm install

# Запустить dev-сервер (порт 5173)
npm run dev
```

Dev-режим работает без реального Telegram: запросы к API отправляются с заголовком `X-Init-Data: "dev"`, который принимается бэкендом при `APP_ENV=development`.

**Требование:** API-сервер должен быть запущен на `http://localhost:8081` (см. `miniapp/.env.development`).

```bash
# Запустить API-сервер отдельно
cd ..
APP_ENV=development python run_master.py
```

## Сборка и деплой

```bash
# Из корня проекта

# Только сборка (генерирует miniapp/dist/)
./build_miniapp.sh

# Полный деплой: сборка → rsync на сервер → nginx reload
./deploy_miniapp.sh
```

Деплой загружает статику в `/var/www/app.crmfit.ru/` на сервере `75.119.153.118`.
Nginx раздаёт на `https://app.crmfit.ru`.

## API эндпоинты

Все запросы идут на `https://api.crmfit.ru` (в dev — `http://localhost:8081`).
Аутентификация через заголовок `X-Init-Data` (Telegram initData или `"dev"` в dev-режиме).

| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/me` | Данные клиента, мастера, баланс бонусов |
| GET | `/api/orders` | История заказов клиента |
| GET | `/api/bonuses` | Баланс и лог бонусных операций |
| GET | `/api/services` | Список услуг мастера |
| GET | `/api/promos` | Активные акции |
| POST | `/api/orders/request` | Создать заявку на услугу |
| GET | `/health` | Health check |

## BotFather — подключение Mini App

1. Открыть [@BotFather](https://t.me/BotFather)
2. `/newapp` → выбрать client_bot → указать `https://app.crmfit.ru` как Web App URL
3. После создания Mini App кнопка автоматически появится в боте (настраивается в `src/client_bot.py`)

## Структура файлов

```
miniapp/
├── public/
│   ├── favicon.svg
│   └── icons.svg              # SVG-спрайт для иконок навигации
├── src/
│   ├── api/
│   │   └── client.js          # axios instance + interceptor для X-Init-Data
│   ├── components/
│   │   ├── BottomNav.jsx      # Нижняя навигация (4 вкладки)
│   │   ├── ErrorScreen.jsx    # Экран ошибки с кнопкой повтора
│   │   └── Skeleton.jsx       # Skeleton-плейсхолдер при загрузке
│   ├── pages/
│   │   ├── Home.jsx           # Главная страница
│   │   ├── Booking.jsx        # Форма записи
│   │   ├── Bonuses.jsx        # Бонусы и история заказов
│   │   └── Promos.jsx         # Акции
│   ├── App.jsx                # Роутинг + BackButton управление
│   ├── main.jsx               # QueryClient + WebApp.ready()
│   └── theme.css              # CSS-переменные Telegram theme
├── .env.development           # VITE_API_URL=http://localhost:8081
├── .env.production            # VITE_API_URL=https://api.crmfit.ru
├── vite.config.js
└── package.json
```
