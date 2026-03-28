# Промпт: Mini App — Этап 3 — Интеграция, деплой, кнопка в боте

## Контекст проекта

Прочитай перед началом:
- `main.py` — структура запуска компонентов
- `src/client_bot.py` — клиентский бот, функция `main()` и `home_client_kb()`
- `src/keyboards.py` — все клавиатуры
- `src/config.py` — переменные окружения
- `miniapp/vite.config.js` — конфиг сборки

Архитектура сервера:
- Python боты — Docker контейнеры (`docker-compose.yml`)
- FastAPI — порт 8081 проброшен из контейнера на хост (`127.0.0.1:8081:8081`)
- nginx — на хосте, проксирует запросы
- Папка проекта на сервере: `/opt/master_bot/`
- Домены: `app.crmfit.ru` (Mini App фронт), `api.crmfit.ru` (FastAPI)

---

## Задача 1 — Кнопка Mini App в client_bot

### 1.1 Кнопка меню бота (Menu Button)

В `src/client_bot.py` в функции `main()` после `set_my_commands` добавить:

```python
from aiogram.types import MenuButtonWebApp, WebAppInfo
from src.config import MINIAPP_URL

await bot.set_chat_menu_button(
    menu_button=MenuButtonWebApp(
        text="📱 Открыть приложение",
        web_app=WebAppInfo(url=MINIAPP_URL)
    )
)
```

Эта кнопка появляется слева от поля ввода и открывает Mini App.

### 1.2 Кнопка на Home экране

В `src/keyboards.py` найти функцию `home_client_kb()`.
Добавить отдельной строкой кнопку Mini App:

```python
from aiogram.types import WebAppInfo
from src.config import MINIAPP_URL

# Добавить в конец клавиатуры отдельной строкой:
[InlineKeyboardButton(
    text="📱 Открыть приложение",
    web_app=WebAppInfo(url=MINIAPP_URL)
)]
```

Внимательно изучи текущую структуру `home_client_kb()` перед правкой — не нарушить существующие кнопки.

---

## Задача 2 — Скрипт сборки фронта

Создать `build_miniapp.sh` в корне проекта:

```bash
#!/bin/bash
set -e

echo "=== Building Mini App ==="
cd miniapp
npm install
npm run build
cd ..
echo "=== Build complete: miniapp/dist/ ==="
ls -la miniapp/dist/
```

---

## Задача 3 — Скрипт деплоя фронта

Создать `deploy_miniapp.sh` в корне проекта:

```bash
#!/bin/bash
set -e

SERVER="deploy@75.119.153.118"
REMOTE_DIR="/opt/master_bot/miniapp/dist"

echo "=== Building Mini App ==="
cd miniapp
npm install
npm run build
cd ..

echo "=== Creating remote directory ==="
ssh $SERVER "mkdir -p $REMOTE_DIR"

echo "=== Uploading dist/ to server ==="
rsync -avz --delete miniapp/dist/ $SERVER:$REMOTE_DIR/

echo "=== Reloading nginx ==="
ssh $SERVER "sudo nginx -t && sudo systemctl reload nginx"

echo ""
echo "=== Done! ==="
echo "Mini App: https://app.crmfit.ru"
```

---

## Задача 4 — nginx конфигурация

Создать папку `nginx/` в корне проекта.
Создать файл `nginx/miniapp.conf`:

```nginx
# Mini App frontend — app.crmfit.ru
server {
    listen 80;
    server_name app.crmfit.ru;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name app.crmfit.ru;

    ssl_certificate /etc/letsencrypt/live/crmfit.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/crmfit.ru/privkey.pem;

    root /opt/master_bot/miniapp/dist;
    index index.html;

    # SPA routing — все пути отдаём index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Кэш статических ресурсов
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}

# FastAPI backend — api.crmfit.ru
server {
    listen 80;
    server_name api.crmfit.ru;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.crmfit.ru;

    ssl_certificate /etc/letsencrypt/live/crmfit.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/crmfit.ru/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # CORS — дублируем на уровне nginx
        add_header Access-Control-Allow-Origin "https://app.crmfit.ru" always;
        add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Content-Type, X-Init-Data" always;

        if ($request_method = OPTIONS) {
            return 204;
        }
    }
}
```

Добавить в README инструкцию по установке конфига:
```bash
# На сервере — один раз:
sudo cp /opt/master_bot/nginx/miniapp.conf /etc/nginx/sites-available/miniapp.conf
sudo ln -sf /etc/nginx/sites-available/miniapp.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

---

## Задача 5 — Обновить .env.example

В `.env.example` убедиться что есть:

```
# Mini App
APP_ENV=production
API_PORT=8081
MINIAPP_URL=https://app.crmfit.ru
```

---

## Задача 6 — Обновить README.md

Добавить раздел **Mini App** в `README.md`:

```markdown
## Mini App

### Локальная разработка

```bash
# 1. Запустить бэкенд (в .env установить APP_ENV=development)
python main.py

# 2. Запустить фронтенд (в отдельном терминале)
cd miniapp
npm run dev
# Открыть: http://localhost:5173
```

Dev режим: фронт автоматически использует `X-Init-Data: dev`.
Бэкенд в режиме `APP_ENV=development` принимает `dev` без проверки HMAC.

### Сборка фронта

```bash
./build_miniapp.sh
# Результат: miniapp/dist/
```

### Деплой фронта на сервер

```bash
./deploy_miniapp.sh
# Собирает локально, заливает rsync на /opt/master_bot/miniapp/dist/
# Перезагружает nginx
```

### Первоначальная настройка nginx на сервере (один раз)

```bash
ssh deploy@75.119.153.118
sudo cp /opt/master_bot/nginx/miniapp.conf /etc/nginx/sites-available/miniapp.conf
sudo ln -sf /etc/nginx/sites-available/miniapp.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### BotFather настройка (один раз после деплоя)

В BotFather для client_bot:
```
/setmenubutton → выбрать бота → Configure menu button
→ Web App
→ URL: https://app.crmfit.ru
→ Button text: Открыть приложение
```
```

---

## Критерии проверки

1. `./build_miniapp.sh` — выполняется без ошибок, `miniapp/dist/` создаётся
2. `./deploy_miniapp.sh` — rsync заливает файлы, nginx перезагружается
3. `src/keyboards.py` `home_client_kb()` — содержит кнопку `web_app` с `MINIAPP_URL`
4. `src/client_bot.py` `main()` — вызывается `set_chat_menu_button()` с WebApp
5. `nginx/miniapp.conf` — создан с конфигами для `app.crmfit.ru` и `api.crmfit.ru`
6. `.env.example` — содержит `APP_ENV`, `API_PORT`, `MINIAPP_URL`
7. `README.md` — обновлён, есть раздел Mini App с инструкциями деплоя
