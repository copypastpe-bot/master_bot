# Mini App — Этап 3 — Deploy Design

**Date:** 2026-03-21
**Status:** Approved

## Goal

Интегрировать Mini App в client_bot (кнопки) и задеплоить фронт + API на production-домены.

## Architecture

**Frontend:** статика собирается локально (`npm run build`), загружается rsync в `/var/www/app.crmfit.ru/` на сервере. nginx раздаёт на `https://app.crmfit.ru`.

**API:** FastAPI уже работает на `127.0.0.1:8081` в Docker. nginx проксирует на `https://api.crmfit.ru`.

**SSL:** используем существующий cert `/etc/letsencrypt/live/masterbot.crmfit.ru/` + выпускаем новый через certbot для `app.crmfit.ru` и `api.crmfit.ru`.

## Key Decisions

- **Деплой фронта:** вариант A — сборка локально + rsync (Node.js не нужен на сервере, Docker не трогаем)
- **SSL cert path:** `live/masterbot.crmfit.ru/` — именно этот cert есть на сервере (промпт предполагал `live/crmfit.ru/`)
- **Static dir:** `/var/www/app.crmfit.ru/` (а не `/var/www/master_bot/miniapp/dist/` как в промпте)
- **Restart:** без `systemctl restart master_bot` — у нас Docker, не systemd

## Tasks

### 1. client_bot кнопки
- `src/keyboards.py` → `home_client_kb()`: новая строка с `InlineKeyboardButton(web_app=WebAppInfo(url=MINIAPP_URL))`
- `src/client_bot.py` → `main()`: `set_chat_menu_button(MenuButtonWebApp(...))` после `set_my_commands`

### 2. build_miniapp.sh
Скрипт в корне: `npm install && npm run build` в `miniapp/`.

### 3. nginx/miniapp.conf
Два server-блока:
- `app.crmfit.ru` → static `/var/www/app.crmfit.ru/`, SPA routing (`try_files $uri /index.html`), static assets cache 1y
- `api.crmfit.ru` → proxy `http://127.0.0.1:8081`, CORS headers

### 4. deploy_miniapp.sh
```
1. npm run build локально
2. rsync dist/ → deploy@75.119.153.118:/var/www/app.crmfit.ru/
3. scp nginx/miniapp.conf → сервер
4. ssh: sudo nginx -t && sudo systemctl reload nginx
```

### 5. .env.example
Проверить наличие `APP_ENV`, `API_PORT`, `MINIAPP_URL`.

### 6. README.md
Добавить раздел Mini App: dev, деплой, сборка, BotFather инструкция.

## Server Info

- Server: `deploy@75.119.153.118`
- Project: `/opt/master_bot/`
- Static dir (new): `/var/www/app.crmfit.ru/`
- SSL cert: `/etc/letsencrypt/live/masterbot.crmfit.ru/fullchain.pem`
- nginx sites: `/etc/nginx/sites-available/` → symlink в `sites-enabled/`
