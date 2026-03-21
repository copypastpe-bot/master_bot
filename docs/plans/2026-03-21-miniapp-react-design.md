# Mini App — React Frontend Design

**Date:** 2026-03-21
**Status:** Approved

## Overview

React + Vite SPA в папке `miniapp/` — клиентский интерфейс для Telegram Mini App.
Подключается к FastAPI бэкенду на порту 8081 (уже реализован).

## Stack

- React + Vite (template react)
- @twa-dev/sdk — Telegram WebApp API
- @tanstack/react-query — data fetching / caching
- axios — HTTP клиент
- Чистый CSS (без UI-библиотек) — полный контроль над Telegram-темой

## Routing

`useState`-навигация в App.jsx (без react-router). Обоснование: Telegram Mini App не поддерживает deep links, browser history не нужен, минимальный бандл.

## Dev Bypass (A2)

**Проблема:** Telegram `initData` требует HMAC-валидации на бэкенде.
**Решение:**
- Backend (`src/api/dependencies.py`): если `APP_ENV=development` и `X-Init-Data: "dev"` → возвращать тестового клиента без HMAC
- Frontend (`src/api/client.js`): если `import.meta.env.DEV` → подставлять `"dev"` вместо `WebApp.initData`

## Structure

```
miniapp/
├── index.html
├── vite.config.js              — proxy /api → localhost:8081
├── package.json
├── .env.development            — VITE_API_URL=http://localhost:8081
├── .env.production             — VITE_API_URL=https://api.crmfit.ru
└── src/
    ├── main.jsx                — QueryClient + WebApp.ready() + WebApp.expand()
    ├── App.jsx                 — useState routing, BackButton logic
    ├── theme.css               — CSS vars из Telegram темы + skeleton animation
    ├── api/client.js           — axios instance + dev bypass + все запросы
    ├── pages/
    │   ├── Home.jsx            — приветствие, баланс, ближайшая запись, лог бонусов
    │   ├── Booking.jsx         — сетка услуг, MainButton, экран успеха
    │   ├── Bonuses.jsx         — 2 вкладки: лог / история заказов
    │   └── Promos.jsx          — карточки акций, empty state
    └── components/
        ├── BottomNav.jsx       — 4 вкладки с inline SVG иконками
        ├── Skeleton.jsx        — пульсирующий placeholder
        └── ErrorScreen.jsx     — ошибка + кнопка retry
```

## Pages

### Home
Данные: `/api/me`, `/api/orders`, `/api/bonuses`
Блоки: шапка с аватаром (инициалы), карточка баланса, ближайшая запись (статус new/confirmed, дата в будущем), последние 3 бонусные операции.

### Booking
Данные: `/api/services`
Сетка 2 колонки, выбор услуги, textarea комментарий, MainButton → POST `/api/orders/request`.
Валидация: услуга обязательна → haptic error + подсветка.
После успеха: haptic success + экран подтверждения.

### Bonuses
Данные: `/api/bonuses`, `/api/orders`
Две вкладки (локальный state): лог бонусов (иконки/цвета по типу) и история заказов (статусы).

### Promos
Данные: `/api/promos`
Карточки с датой окончания. Empty state если список пуст.

## Telegram Integration

- `WebApp.expand()` при старте
- `BackButton` на всех страницах кроме Home → navigate('home')
- `MainButton` только на Booking
- `HapticFeedback.impactOccurred('light')` на кнопках
- `HapticFeedback.notificationOccurred('success'/'error')` на событиях

## Criteria

1. `npm run dev` без ошибок
2. `npm run build` собирается в `dist/`
3. Все страницы загружают данные, skeleton при загрузке
4. Booking: выбор услуги + отправка заявки работает
5. Тема адаптируется к Telegram CSS переменным
