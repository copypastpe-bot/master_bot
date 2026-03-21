# Mini App Deploy Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Интегрировать Mini App кнопки в client_bot и задеплоить фронт (`app.crmfit.ru`) + API (`api.crmfit.ru`) на production.

**Architecture:** Фронт собирается локально через `npm run build`, загружается rsync на сервер в `/var/www/app.crmfit.ru/`. nginx раздаёт статику и проксирует FastAPI (уже в Docker на порту 8081). SSL — certbot на subdomains.

**Tech Stack:** aiogram 3.x (MenuButtonWebApp, WebAppInfo), bash (rsync, ssh), nginx, certbot, Vite

---

## Task 1: Кнопка Mini App в keyboards.py

**Files:**
- Modify: `src/keyboards.py:648-667`

**Context:**
`home_client_kb()` расположена на строке 648. Функция возвращает `InlineKeyboardMarkup`.
`MINIAPP_URL` уже есть в `src/config.py` как `MINIAPP_URL: str = os.getenv("MINIAPP_URL", "https://app.crmfit.ru")`.

**Step 1: Прочитать начало keyboards.py — найти импорты**

```bash
head -30 src/keyboards.py
```

Убедиться что `WebAppInfo` и `InlineKeyboardButton` импортированы. Если нет — добавить в импорты:
```python
from aiogram.types import WebAppInfo
```

**Step 2: Прочитать home_client_kb()**

```bash
sed -n '648,668p' src/keyboards.py
```

**Step 3: Добавить импорт MINIAPP_URL в keyboards.py**

Найти строку с другими импортами из `src.config` (или добавить рядом с другими src-импортами):
```python
from src.config import MINIAPP_URL
```

**Step 4: Добавить кнопку Mini App в home_client_kb()**

Добавить новую строку в конец клавиатуры (перед закрывающей скобкой):
```python
[
    InlineKeyboardButton(
        text="📱 Открыть приложение",
        web_app=WebAppInfo(url=MINIAPP_URL)
    )
],
```

Итоговая функция должна выглядеть:
```python
def home_client_kb() -> InlineKeyboardMarkup:
    """Main menu keyboard for client."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💰 Мои бонусы", callback_data="bonuses"),
            InlineKeyboardButton(text="📋 История", callback_data="history"),
        ],
        [
            InlineKeyboardButton(text="🎁 Акции", callback_data="promos"),
            InlineKeyboardButton(text="📞 Заказать", callback_data="order_request"),
        ],
        [
            InlineKeyboardButton(text="❓ Вопрос", callback_data="question"),
            InlineKeyboardButton(text="📸 Фото/видео", callback_data="media"),
        ],
        [
            InlineKeyboardButton(text="👨‍🔧 Мой мастер", callback_data="master_info"),
            InlineKeyboardButton(text="🔔 Уведомления", callback_data="notifications"),
        ],
        [
            InlineKeyboardButton(
                text="📱 Открыть приложение",
                web_app=WebAppInfo(url=MINIAPP_URL)
            )
        ],
    ])
```

**Step 5: Проверить что импорты не ломают модуль**

```bash
python3 -c "from src.keyboards import home_client_kb; print('OK')"
```
Ожидаем: `OK`

**Step 6: Commit**

```bash
git add src/keyboards.py
git commit -m "feat: add Mini App button to client home keyboard"
```

---

## Task 2: Menu Button в client_bot.py

**Files:**
- Modify: `src/client_bot.py:1967-1972`

**Context:**
В функции `main()` после строки `await bot.set_my_commands([...])` (строка ~1967) нужно добавить вызов `set_chat_menu_button`.

**Step 1: Прочитать блок main() вокруг set_my_commands**

```bash
sed -n '1960,1985p' src/client_bot.py
```

**Step 2: Найти импорты в client_bot.py**

```bash
head -30 src/client_bot.py
```

Убедиться что `MenuButtonWebApp`, `WebAppInfo` импортированы. Если нет — добавить:
```python
from aiogram.types import MenuButtonWebApp, WebAppInfo
```

**Step 3: Добавить импорт MINIAPP_URL**

Рядом с другими импортами из src.config:
```python
from src.config import MINIAPP_URL
```

**Step 4: Добавить set_chat_menu_button после set_my_commands**

После блока `await bot.set_my_commands([...])` добавить:
```python
    await bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(
            text="📱 Открыть приложение",
            web_app=WebAppInfo(url=MINIAPP_URL)
        )
    )
```

**Step 5: Проверить импорты**

```bash
python3 -c "from src.client_bot import main; print('OK')"
```
Ожидаем: `OK`

**Step 6: Commit**

```bash
git add src/client_bot.py
git commit -m "feat: add Mini App menu button to client_bot"
```

---

## Task 3: build_miniapp.sh

**Files:**
- Create: `build_miniapp.sh`

**Step 1: Создать скрипт**

```bash
#!/bin/bash
set -e
echo "Building Mini App..."
cd miniapp
npm install
npm run build
echo "Build complete: miniapp/dist/"
```

**Step 2: Сделать исполняемым**

```bash
chmod +x build_miniapp.sh
```

**Step 3: Запустить и убедиться что работает**

```bash
./build_miniapp.sh
```
Ожидаем в конце: `Build complete: miniapp/dist/` и `✓ built in ...ms`

**Step 4: Commit**

```bash
git add build_miniapp.sh
git commit -m "feat: add build_miniapp.sh script"
```

---

## Task 4: nginx/miniapp.conf

**Files:**
- Create: `nginx/miniapp.conf`

**Context:**
- SSL cert на сервере: `/etc/letsencrypt/live/masterbot.crmfit.ru/fullchain.pem`
- Static dir: `/var/www/app.crmfit.ru/`
- API proxy: `http://127.0.0.1:8081`
- Includes: `/etc/letsencrypt/options-ssl-nginx.conf` и `/etc/letsencrypt/ssl-dhparams.pem`

**Step 1: Создать директорию nginx/**

```bash
mkdir -p nginx
```

**Step 2: Создать nginx/miniapp.conf**

```nginx
# Mini App frontend — app.crmfit.ru
server {
    listen 80;
    listen [::]:80;
    server_name app.crmfit.ru;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name app.crmfit.ru;

    ssl_certificate /etc/letsencrypt/live/app.crmfit.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.crmfit.ru/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    root /var/www/app.crmfit.ru;
    index index.html;

    # SPA routing — all routes to index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets 1 year
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}

# FastAPI backend — api.crmfit.ru
server {
    listen 80;
    listen [::]:80;
    server_name api.crmfit.ru;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name api.crmfit.ru;

    ssl_certificate /etc/letsencrypt/live/api.crmfit.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.crmfit.ru/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    location / {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Handle CORS preflight
        if ($request_method = OPTIONS) {
            add_header Access-Control-Allow-Origin "https://app.crmfit.ru";
            add_header Access-Control-Allow-Methods "GET, POST, OPTIONS";
            add_header Access-Control-Allow-Headers "Content-Type, X-Init-Data";
            return 204;
        }
    }
}
```

**Note:** SSL cert paths для `app.crmfit.ru` и `api.crmfit.ru` будут созданы certbot в Task 6.

**Step 3: Commit**

```bash
git add nginx/miniapp.conf
git commit -m "feat: add nginx config for app.crmfit.ru and api.crmfit.ru"
```

---

## Task 5: deploy_miniapp.sh

**Files:**
- Create: `deploy_miniapp.sh`

**Context:**
- Server: `deploy@75.119.153.118`
- Static dir: `/var/www/app.crmfit.ru/`
- nginx config: `/etc/nginx/sites-available/miniapp.conf`

**Step 1: Создать deploy_miniapp.sh**

```bash
#!/bin/bash
set -e

SERVER="deploy@75.119.153.118"
STATIC_DIR="/var/www/app.crmfit.ru"

echo "=== Building Mini App ==="
cd miniapp
npm install --silent
npm run build
cd ..

echo "=== Creating static dir on server ==="
ssh $SERVER "sudo mkdir -p $STATIC_DIR && sudo chown deploy:deploy $STATIC_DIR"

echo "=== Uploading dist to server ==="
rsync -avz --delete miniapp/dist/ $SERVER:$STATIC_DIR/

echo "=== Uploading nginx config ==="
scp nginx/miniapp.conf $SERVER:/tmp/miniapp.conf
ssh $SERVER "sudo cp /tmp/miniapp.conf /etc/nginx/sites-available/miniapp.conf && \
             sudo ln -sf /etc/nginx/sites-available/miniapp.conf /etc/nginx/sites-enabled/miniapp.conf && \
             sudo nginx -t"

echo "=== Reloading nginx ==="
ssh $SERVER "sudo systemctl reload nginx"

echo ""
echo "=== Done! ==="
echo "Mini App: https://app.crmfit.ru"
echo "API:      https://api.crmfit.ru"
```

**Step 2: Сделать исполняемым**

```bash
chmod +x deploy_miniapp.sh
```

**Step 3: Commit**

```bash
git add deploy_miniapp.sh
git commit -m "feat: add deploy_miniapp.sh script"
```

---

## Task 6: SSL сертификаты на сервере

**Это делается вручную на сервере — не скриптом.**

**Step 1: Проверить что DNS уже распространился**

```bash
nslookup app.crmfit.ru 8.8.8.8
nslookup api.crmfit.ru 8.8.8.8
```
Оба должны вернуть `75.119.153.118`. Если нет — подождать и повторить.

**Step 2: Выпустить сертификаты через certbot**

```bash
ssh deploy@75.119.153.118
sudo certbot certonly --nginx -d app.crmfit.ru
sudo certbot certonly --nginx -d api.crmfit.ru
```

Каждый certbot создаст cert в `/etc/letsencrypt/live/<domain>/`.

**Step 3: Проверить что сертификаты созданы**

```bash
sudo ls /etc/letsencrypt/live/
```
Ожидаем: `app.crmfit.ru/` и `api.crmfit.ru/` в списке.

---

## Task 7: Первый деплой фронта

**Step 1: Запустить deploy_miniapp.sh**

```bash
./deploy_miniapp.sh
```

Ожидаем в конце:
```
=== Done! ===
Mini App: https://app.crmfit.ru
API:      https://api.crmfit.ru
```

**Step 2: Проверить что фронт открывается**

```bash
curl -sI https://app.crmfit.ru | head -5
```
Ожидаем: `HTTP/2 200`

**Step 3: Проверить что API доступен**

```bash
curl -s https://api.crmfit.ru/health
```
Ожидаем: `{"status":"ok"}`

---

## Task 8: Обновить README.md

**Files:**
- Modify: `README.md` (создать если нет)

**Step 1: Прочитать README.md**

```bash
cat README.md 2>/dev/null || echo "FILE_NOT_FOUND"
```

**Step 2: Добавить раздел Mini App**

Добавить (или создать файл с) следующим содержимым:

```markdown
## Mini App

Telegram Mini App для клиентов мастера — бонусы, история, запись, акции.

- Frontend: `https://app.crmfit.ru`
- API: `https://api.crmfit.ru`

### Локальная разработка

```bash
# 1. Запустить бэкенд с dev bypass
APP_ENV=development python run_master.py

# 2. В отдельном терминале — фронтенд
cd miniapp
npm run dev
# → http://localhost:5173
```

В dev-режиме API автоматически использует `X-Init-Data: dev`
(бэкенд принимает без HMAC при `APP_ENV=development`).

### Деплой

```bash
./deploy_miniapp.sh
```

Скрипт: собирает фронт локально, загружает rsync на сервер,
обновляет nginx конфиг.

### Ручная сборка фронта

```bash
./build_miniapp.sh
# → miniapp/dist/
```

### Настройка кнопки в BotFather

После деплоя — в BotFather для client_bot:
1. `/mybots` → выбрать бота → Bot Settings → Menu Button
2. Тип: Web App
3. URL: `https://app.crmfit.ru`
4. Текст: `Открыть приложение`

Или через команду в чате с BotFather:
```
/setmenubutton
→ выбрать бота
→ Configure menu button
→ Web App
→ url: https://app.crmfit.ru
→ text: Открыть приложение
```
```

**Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add Mini App section to README"
```

---

## Task 9: Push и деплой ботов

**Step 1: Push всех изменений**

```bash
git push origin main
```

**Step 2: Задеплоить боты на сервер (с обновлёнными keyboards.py и client_bot.py)**

```bash
ssh deploy@75.119.153.118 "cd /opt/master_bot && git pull && docker compose down && docker compose up -d --build"
```

**Step 3: Проверить что оба бота запустились**

```bash
ssh deploy@75.119.153.118 "docker compose -f /opt/master_bot/docker-compose.yml logs --tail=10"
```

Ожидаем: `Run polling for bot @...` для обоих контейнеров.

**Step 4: Проверить кнопку в Telegram**

Открыть client_bot в Telegram — в интерфейсе должна появиться кнопка "📱 Открыть приложение" как в inline-клавиатуре Home, так и в Menu Button слева от поля ввода.

---

## Контрольный список критериев

| # | Критерий | Команда |
|---|---|---|
| 1 | `./build_miniapp.sh` без ошибок | `./build_miniapp.sh` |
| 2 | `home_client_kb()` содержит `web_app` кнопку | `python3 -c "from src.keyboards import home_client_kb; kb = home_client_kb(); print(kb)"` |
| 3 | `client_bot.py` вызывает `set_chat_menu_button` | `grep set_chat_menu_button src/client_bot.py` |
| 4 | `nginx/miniapp.conf` создан | `ls nginx/miniapp.conf` |
| 5 | `deploy_miniapp.sh` создан и исполняемый | `ls -la deploy_miniapp.sh` |
| 6 | SSL выпущены для обоих subdomains | SSH → `sudo ls /etc/letsencrypt/live/` |
| 7 | `https://app.crmfit.ru` → 200 | `curl -sI https://app.crmfit.ru` |
| 8 | `https://api.crmfit.ru/health` → `{"status":"ok"}` | `curl -s https://api.crmfit.ru/health` |
| 9 | README содержит раздел Mini App | `grep "Mini App" README.md` |
