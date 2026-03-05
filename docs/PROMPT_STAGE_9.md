# Промпт: Этап 9 — Google Calendar OAuth + синхронизация

## Контекст
Прочитай SPEC.md и google_calendar.py (там заглушка) перед началом.
Модуль google_calendar.py уже существует — заменить заглушки на реальную реализацию.

---

## Архитектура

Три компонента работают параллельно:
1. `master_bot.py` — бот мастера
2. `client_bot.py` — бот клиента  
3. `oauth_server.py` — aiohttp сервер для OAuth callback

Все три запускаются из одной точки входа `main.py`:
```python
async def main():
    await asyncio.gather(
        run_master_bot(),
        run_client_bot(),
        run_oauth_server(),
    )
```

---

## oauth_server.py

Минимальный aiohttp сервер на порту из `.env` (default: 8080).
```python
from aiohttp import web

async def handle_oauth_callback(request):
    code = request.rel_url.query.get('code')
    state = request.rel_url.query.get('state')  # содержит master_id
    error = request.rel_url.query.get('error')
    ...
```

**Один эндпоинт:** `GET /oauth/callback`

Параметры от Google:
- `code` — код авторизации
- `state` — `master_id` (передаём при генерации URL)
- `error` — если пользователь отказал

**Логика:**
1. Если `error` — сохранить статус ошибки, уведомить мастера в master_bot
2. Если `code` — обменять на токен, сохранить в БД, уведомить мастера

После успешной авторизации — уведомить мастера через master_bot:
```
✅ Google Calendar подключён!

Аккаунт: example@gmail.com
Теперь все заказы будут автоматически
появляться в вашем календаре.
```

После ошибки/отказа:
```
❌ Google Calendar не подключён.

Вы отменили авторизацию или произошла ошибка.
Попробуйте снова в Настройках.
```

Redirect URI в `.env`:
```
OAUTH_REDIRECT_URI=https://yourdomain.com/oauth/callback
```

---

## google_calendar.py — полная реализация

### Настройка Google Cloud
Добавить в `.env`:
```
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=https://yourdomain.com/auth/google/callback
```

Scope: `https://www.googleapis.com/auth/calendar.events`

### Функции модуля
```python
async def get_oauth_url(master_id: int) -> str:
    """
    Генерирует URL для авторизации.
    state = str(master_id) — для идентификации мастера в callback.
    """
    flow = Flow.from_client_config(
        client_config={
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uris": [GOOGLE_REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=["https://www.googleapis.com/auth/calendar.events"]
    )
    flow.redirect_uri = GOOGLE_REDIRECT_URI
    url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        state=str(master_id)
    )
    return url

async def exchange_code(master_id: int, code: str) -> str | None:
    """
    Обменивает code на токены.
    Сохраняет credentials JSON в masters.gc_credentials.
    Возвращает email аккаунта или None при ошибке.
    """

async def get_credentials(master_id: int) -> Credentials | None:
    """
    Загружает credentials из БД.
    Автоматически обновляет токен если истёк (refresh_token).
    Сохраняет обновлённые credentials обратно в БД.
    """

async def create_event(master_id: int, order, client) -> str | None:
    """
    Создаёт событие в календаре мастера.
    Возвращает event_id или None если GC не подключён / ошибка.
    """
    credentials = await get_credentials(master_id)
    if not credentials:
        return None
    
    service = build("calendar", "v3", credentials=credentials)
    event = {
        "summary": f"{client.name} — {order.services_text}",
        "description": (
            f"📞 {client.phone}\n"
            f"📍 {order.address}\n"
            f"🛠 {order.services_text}\n"
            f"💰 {order.amount_total} ₽"
        ),
        "start": {
            "dateTime": order.scheduled_at.isoformat(),
            "timeZone": "Europe/Moscow"
        },
        "end": {
            "dateTime": (order.scheduled_at + timedelta(hours=2)).isoformat(),
            "timeZone": "Europe/Moscow"
        }
    }
    result = service.events().insert(calendarId="primary", body=event).execute()
    return result.get("id")

async def update_event(master_id: int, event_id: str, new_dt: datetime) -> bool:
    """Обновляет время события при переносе заказа."""

async def delete_event(master_id: int, event_id: str) -> bool:
    """Удаляет событие при отмене или выполнении заказа."""

async def get_calendar_account(master_id: int) -> str | None:
    """Возвращает email подключённого аккаунта."""
    credentials = await get_credentials(master_id)
    if not credentials:
        return None
    service = build("oauth2", "v2", credentials=credentials)
    info = service.userinfo().get().execute()
    return info.get("email")

async def disconnect_calendar(master_id: int) -> bool:
    """Удаляет credentials из БД."""
```

### Обработка истёкших токенов
```python
async def get_credentials(master_id):
    creds_json = await db.get_gc_credentials(master_id)
    if not creds_json:
        return None
    
    creds = Credentials.from_authorized_user_info(json.loads(creds_json))
    
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Сохранить обновлённые credentials
        await db.save_gc_credentials(master_id, creds.to_json())
    
    return creds if creds.valid else None
```

---

## Настройки мастера — кнопка Google Calendar

Заменить заглушку в профиле мастера на реальный функционал.

**Если не подключён:**
```
📅 Google Calendar
━━━━━━━━━━━━━━━
Статус: ❌ Не подключён

Подключите свой Google Calendar —
заказы будут автоматически появляться
в вашем расписании.

[🔗 Подключить]
[◀️ Назад]  [🏠 Главная]
```

Нажатие «🔗 Подключить»:
1. Генерируем OAuth URL
2. Отправляем мастеру:
```
Перейдите по ссылке для авторизации:
{url}

После авторизации бот получит уведомление
автоматически.
```

**Если подключён:**
```
📅 Google Calendar
━━━━━━━━━━━━━━━
Статус: ✅ Подключён
Аккаунт: example@gmail.com

[❌ Отключить]
[◀️ Назад]  [🏠 Главная]
```

«Отключить» → подтверждение → удалить credentials из БД.

---

## Интеграция с существующим кодом

GC вызывается в четырёх местах в master_bot.py (уже реализованы, но вызывают заглушку):

1. **Создание заказа** — после сохранения в БД:
```python
event_id = await gc.create_event(master_id, order, client)
if event_id:
    await db.save_gc_event_id(order.id, event_id)
```

2. **Перенос заказа** — после обновления времени:
```python
if order.gc_event_id:
    await gc.update_event(master_id, order.gc_event_id, new_dt)
```

3. **Отмена заказа** — после смены статуса:
```python
if order.gc_event_id:
    await gc.delete_event(master_id, order.gc_event_id)
```

4. **Проведение заказа** — после смены статуса на done:
```python
if order.gc_event_id:
    await gc.delete_event(master_id, order.gc_event_id)
```

Все вызовы оборачивать в try/except — GC опционален, ошибка не должна ломать основной flow.

---

## Зависимости

Добавить в requirements.txt:
```
google-auth>=2.0.0
google-auth-oauthlib>=1.0.0
google-api-python-client>=2.0.0
aiohttp>=3.9.0
```

---

## Переменные окружения (.env)
```
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=https://yourdomain.com/auth/google/callback
OAUTH_SERVER_PORT=8090
```

---

## Критерии проверки

1. `main.py` запускает все три компонента одновременно без конфликтов
2. Кнопка «Подключить GC» генерирует рабочую OAuth ссылку
3. После авторизации в браузере — мастер получает уведомление в боте
4. После отказа — мастер получает уведомление об ошибке
5. Статус в настройках обновляется: показывает email аккаунта
6. «Отключить» удаляет credentials, статус меняется на «Не подключён»
7. При создании заказа — событие появляется в GC мастера
8. При переносе — время события обновляется в GC
9. При отмене/проведении — событие удаляется из GC
10. Если токен истёк — автоматически обновляется через refresh_token
11. Если GC не подключён — заказы работают без ошибок
12. Если GC API недоступен — заказы работают без ошибок