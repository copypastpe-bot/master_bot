# Multi-Master Backend Support Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Снять ограничение "один клиент — один мастер": добавить новые функции БД, обновить dependency клиентских API для поддержки `?master_id`, добавить эндпоинты `GET /api/client/masters` и `POST /api/client/link`, обновить `client_bot.py` для показа выбора мастера при нескольких.

**Architecture:** Три новые функции в `database.py`. `get_current_client` в `dependencies.py` принимает опциональный `?master_id` query param — при 1 мастере backward compat, при 2+ без master_id → 400. Отдельный роутер `client_masters.py`. В `client_bot.py` — module-level dict `_active_masters` для хранения выбранного мастера (не зависит от FSM state.clear()).

**Tech Stack:** Python, FastAPI, aiosqlite, aiogram 3.x

---

### Task 1: Три новые функции в database.py

**Files:**
- Modify: `src/database.py`

**Контекст:** Смотри существующие функции `get_master_client` (строка ~678) и `link_client_to_master` (~655) как образцы паттерна подключения к БД.

**Step 1: Добавить `get_client_masters`**

После функции `get_master_client_by_client_tg_id` (~строка 709) добавить:

```python
async def get_client_masters(client_id: int) -> list[dict]:
    """Get all masters linked to a client, ordered by last visit."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT m.id as master_id, m.name as master_name, m.sphere,
                   mc.bonus_balance, mc.last_visit,
                   (SELECT COUNT(*) FROM orders
                    WHERE master_id = m.id AND client_id = ? AND status = 'done') as order_count
            FROM masters m
            JOIN master_clients mc ON m.id = mc.master_id
            WHERE mc.client_id = ?
            ORDER BY mc.last_visit DESC NULLS LAST
            """,
            (client_id, client_id),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await conn.close()


async def get_all_client_masters_by_tg_id(tg_id: int) -> list[dict]:
    """Get all masters for a client by their Telegram ID. Returns [] if not found."""
    client = await get_client_by_tg_id(tg_id)
    if not client:
        return []
    return await get_client_masters(client.id)


async def link_existing_client_to_master(client_id: int, master_id: int) -> bool:
    """Link existing client to a new master.
    Returns True if linked, False if already linked.
    """
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            INSERT INTO master_clients (master_id, client_id)
            VALUES (?, ?)
            ON CONFLICT(master_id, client_id) DO NOTHING
            """,
            (master_id, client_id),
        )
        await conn.commit()
        return cursor.rowcount > 0
    finally:
        await conn.close()
```

**Step 2: Проверить импорт**

```bash
cd /Users/evgenijpastusenko/Projects/Master_bot
python -c "
from src.database import get_client_masters, get_all_client_masters_by_tg_id, link_existing_client_to_master
print('OK')
"
```

Ожидаемый вывод: `OK`

**Step 3: Commit**

```bash
git add src/database.py
git commit -m "feat(db): add get_client_masters, get_all_client_masters_by_tg_id, link_existing_client_to_master"
```

---

### Task 2: Обновить get_current_client в dependencies.py

**Files:**
- Modify: `src/api/dependencies.py`

**Контекст:** Текущая функция `get_current_client` (~строка 41) использует `get_master_client_by_client_tg_id` с LIMIT 1. Нужно заменить логику получения мастера, добавить `master_id: Optional[int] = Query(None)`. Сигнатура и название остаются — все 5 роутеров не трогаем.

**Step 1: Добавить импорты**

В начало `src/api/dependencies.py` добавить в существующий блок импортов:

```python
from fastapi import Header, HTTPException, Query  # добавить Query
from src.database import (
    get_client_by_tg_id,          # уже есть
    get_master_client_by_client_tg_id,  # уже есть — можно оставить для dev bypass
    get_master_by_id,              # уже есть
    get_masters,                   # уже есть
    get_master_by_tg_id,           # уже есть
    get_master_client,             # уже есть
    get_all_client_masters_by_tg_id,   # НОВОЕ
)
```

**Step 2: Заменить функцию `get_current_client`**

Найти функцию `get_current_client` (начинается ~строка 41) и заменить целиком:

```python
async def get_current_client(
    master_id: Optional[int] = Query(None),
    x_init_data: Optional[str] = Header(None, alias="X-Init-Data"),
) -> Tuple[Client, Master, MasterClient]:
    """
    Dependency - validate initData and return (client, master, master_client).

    Master determined by:
    1. ?master_id=X query param (explicit)
    2. If client has only 1 master → use that one (backward compat)
    3. If client has multiple masters and no master_id → HTTP 400

    In development mode with X-Init-Data: "dev" — returns first DB client without HMAC check.
    Raises 401 if invalid, 404 if client not found.
    """
    if not x_init_data:
        raise HTTPException(status_code=401, detail="Missing X-Init-Data header")

    # Dev bypass — unchanged behaviour
    if APP_ENV == "development" and x_init_data == "dev":
        return await _get_dev_client()

    validated = validate_init_data(x_init_data, CLIENT_BOT_TOKEN)
    if not validated:
        raise HTTPException(status_code=401, detail="Invalid initData")

    tg_id = extract_tg_id(validated)
    if not tg_id:
        raise HTTPException(status_code=401, detail="No user data")

    client = await get_client_by_tg_id(tg_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not registered")

    masters = await get_all_client_masters_by_tg_id(tg_id)
    if not masters:
        raise HTTPException(status_code=404, detail="Not linked to any master")

    if master_id is not None:
        entry = next((m for m in masters if m["master_id"] == master_id), None)
        if entry is None:
            raise HTTPException(status_code=403, detail="Not linked to this master")
        chosen_master_id = master_id
    elif len(masters) == 1:
        chosen_master_id = masters[0]["master_id"]
    else:
        raise HTTPException(
            status_code=400,
            detail="Укажите master_id: у вас несколько мастеров",
        )

    master = await get_master_by_id(chosen_master_id)
    if not master:
        raise HTTPException(status_code=404, detail="Master not found")

    master_client = await get_master_client(chosen_master_id, client.id)
    if not master_client:
        raise HTTPException(status_code=404, detail="Master-client link not found")

    return client, master, master_client
```

**Step 3: Проверить что сервер запускается**

```bash
python -c "from src.api.app import app; print('OK')"
```

Ожидаемый вывод: `OK`

**Step 4: Commit**

```bash
git add src/api/dependencies.py
git commit -m "feat(api): update get_current_client to support multi-master via ?master_id"
```

---

### Task 3: Создать роутер client_masters.py

**Files:**
- Create: `src/api/routers/client_masters.py`
- Modify: `src/api/app.py`

**Контекст:** Смотри `src/api/routers/client.py` как образец структуры роутера. Оба эндпоинта принимают только `x_init_data` (без `get_current_client` dependency — нам не нужен конкретный мастер).

**Step 1: Создать файл**

```python
"""Client multi-master endpoints: list masters, link to new master."""

from typing import Optional
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from src.api.auth import validate_init_data, extract_tg_id
from src.config import CLIENT_BOT_TOKEN, APP_ENV
from src.database import (
    get_client_by_tg_id,
    get_master_by_invite_token,
    get_all_client_masters_by_tg_id,
    link_existing_client_to_master,
    accrue_welcome_bonus,
    get_masters,
)

router = APIRouter(tags=["client-masters"])


async def _resolve_tg_id(x_init_data: Optional[str]) -> int:
    """Validate initData and return tg_id. Raises 401 on failure."""
    if not x_init_data:
        raise HTTPException(status_code=401, detail="Missing X-Init-Data header")
    if APP_ENV == "development" and x_init_data == "dev":
        masters = await get_masters()
        # Dev: return a fake tg_id that won't match real clients
        return 999999999
    validated = validate_init_data(x_init_data, CLIENT_BOT_TOKEN)
    if not validated:
        raise HTTPException(status_code=401, detail="Invalid initData")
    from src.api.auth import extract_tg_id
    tg_id = extract_tg_id(validated)
    if not tg_id:
        raise HTTPException(status_code=401, detail="No user data")
    return tg_id


@router.get("/client/masters")
async def get_client_masters_list(
    x_init_data: Optional[str] = Header(None, alias="X-Init-Data"),
):
    """Return all masters linked to this client."""
    tg_id = await _resolve_tg_id(x_init_data)
    masters = await get_all_client_masters_by_tg_id(tg_id)
    return {"masters": masters, "count": len(masters)}


class LinkMasterRequest(BaseModel):
    invite_token: str


@router.post("/client/link")
async def link_to_master(
    body: LinkMasterRequest,
    x_init_data: Optional[str] = Header(None, alias="X-Init-Data"),
):
    """Link this client to a new master via invite token."""
    tg_id = await _resolve_tg_id(x_init_data)

    client = await get_client_by_tg_id(tg_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not registered")

    master = await get_master_by_invite_token(body.invite_token)
    if not master:
        raise HTTPException(status_code=404, detail="Invite token not found")

    linked = await link_existing_client_to_master(client.id, master.id)
    if not linked:
        raise HTTPException(status_code=409, detail="Already linked to this master")

    # Accrue welcome bonus if configured (idempotent — won't double-accrue)
    await accrue_welcome_bonus(master.id, client.id)

    # Return master info with fresh bonus balance
    masters = await get_all_client_masters_by_tg_id(tg_id)
    entry = next((m for m in masters if m["master_id"] == master.id), {})

    return {
        "master_id": master.id,
        "name": master.name,
        "sphere": master.sphere,
        "bonus_balance": entry.get("bonus_balance", 0),
    }
```

**Step 2: Подключить роутер в app.py**

В `src/api/app.py` добавить:

```python
from src.api.routers import client_masters  # добавить в блок импортов роутеров
```

И после `app.include_router(auth_router.router, prefix="/api")`:

```python
app.include_router(client_masters.router, prefix="/api")
```

**Step 3: Проверить маршруты**

```bash
python -c "
from src.api.app import app
routes = [r.path for r in app.routes]
assert '/api/client/masters' in routes, f'missing: {routes}'
assert '/api/client/link' in routes, f'missing: {routes}'
print('OK')
"
```

Ожидаемый вывод: `OK`

**Step 4: Commit**

```bash
git add src/api/routers/client_masters.py src/api/app.py
git commit -m "feat(api): add GET /client/masters and POST /client/link endpoints"
```

---

### Task 4: Добавить master_id в OrderRequest

**Files:**
- Modify: `src/api/routers/orders.py`

**Контекст:** `OrderRequest` (строка ~23) — Pydantic модель. `create_order_request` (строка ~52) получает `(client, master, master_client)` из dependency. Если в body передан `master_id` — нужно переопределить мастера из dependency (для клиентов с несколькими мастерами, которые не передают query param).

**Step 1: Обновить `OrderRequest`**

Найти класс `OrderRequest` и заменить:

```python
class OrderRequest(BaseModel):
    """Order request from Mini App."""
    service_name: str
    master_id: Optional[int] = None  # для мультимастерных клиентов
    comment: Optional[str] = None
```

**Step 2: Проверить синтаксис**

```bash
python -c "from src.api.routers.orders import router; print('OK')"
```

Ожидаемый вывод: `OK`

**Step 3: Commit**

```bash
git add src/api/routers/orders.py
git commit -m "feat(api): add optional master_id to OrderRequest body"
```

---

### Task 5: Обновить get_client_context в client_bot.py

**Files:**
- Modify: `src/client_bot.py`

**Контекст:** `get_client_context` (~строка 148) сейчас читает `client.registered_via`. Нужно использовать `get_all_client_masters_by_tg_id`. Для хранения выбранного мастера — module-level dict `_active_masters: dict[int, int]` (tg_id → master_id). Это не зависит от `state.clear()`.

**Step 1: Добавить новые импорты из database**

В блок импортов из `src.database` добавить:

```python
get_all_client_masters_by_tg_id,
link_existing_client_to_master,  # на будущее
```

**Step 2: Добавить module-level dict после `master_bot: Bot = None`**

```python
# Active master selection for multi-master clients (tg_id → master_id)
_active_masters: dict[int, int] = {}
```

**Step 3: Заменить функцию `get_client_context`**

Найти и заменить целиком (~строка 148–159):

```python
async def get_client_context(tg_id: int, master_id: int = None) -> tuple:
    """Get client, master, and master_client for a user.

    If master_id specified → use that master.
    If client has 1 master → use that one (backward compat).
    If client has multiple and no master_id → return (client, None, None).
    """
    client = await get_client_by_tg_id(tg_id)
    if not client:
        return None, None, None

    masters = await get_all_client_masters_by_tg_id(tg_id)
    if not masters:
        return client, None, None

    if master_id:
        entry = next((m for m in masters if m["master_id"] == master_id), None)
        if not entry:
            return client, None, None
    elif len(masters) == 1:
        master_id = masters[0]["master_id"]
    else:
        # Multiple masters, no selection — caller must handle
        return client, None, None

    master = await get_master_by_id(master_id)
    if not master:
        return client, None, None

    master_client = await get_master_client(master_id, client.id)
    return client, master, master_client
```

**Step 4: Добавить `get_master_client` в импорты из database** (если не импортирован)

Проверить строку импортов из `src.database` — функция `get_master_client` уже должна быть там. Если нет — добавить.

**Step 5: Обновить все вызовы `get_client_context(tg_id)` для передачи active_master_id**

Найти все вхождения: `grep -n "get_client_context(tg_id)" src/client_bot.py`

Для каждого вхождения (кроме тех, что внутри самой функции) заменить:

```python
# БЫЛО:
client, master, master_client = await get_client_context(tg_id)

# СТАЛО:
client, master, master_client = await get_client_context(tg_id, _active_masters.get(tg_id))
```

**Важно:** В `HomeButtonMiddleware` вместо `tg_id = event.from_user.id` и затем вызова, паттерн такой же.

**Step 6: Проверить синтаксис**

```bash
python -c "from src.client_bot import router; print('OK')"
```

Ожидаемый вывод: `OK`

**Step 7: Commit**

```bash
git add src/client_bot.py
git commit -m "feat(bot): update get_client_context to support multi-master via _active_masters dict"
```

---

### Task 6: Добавить UI выбора мастера в client_bot.py

**Files:**
- Modify: `src/client_bot.py`

**Контекст:** Когда `get_client_context` возвращает `(client, None, None)` и клиент зарегистрирован (есть мастера) — нужно показать кнопки выбора. После выбора записать в `_active_masters[tg_id] = master_id` и показать Home.

**Step 1: Добавить функцию `show_master_select`**

После функции `get_client_context` (~строка 180) добавить:

```python
async def show_master_select(bot: Bot, tg_id: int, chat_id: int) -> None:
    """Show inline keyboard for selecting active master."""
    masters = await get_all_client_masters_by_tg_id(tg_id)
    if not masters:
        await bot.send_message(chat_id, "Вы не привязаны ни к одному мастеру.")
        return

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    buttons = [
        [InlineKeyboardButton(
            text=f"{m['master_name']}" + (f" · {m['sphere']}" if m.get('sphere') else ""),
            callback_data=f"select_master:{m['master_id']}",
        )]
        for m in masters
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await bot.send_message(
        chat_id,
        "👥 У вас несколько мастеров. Выберите:",
        reply_markup=keyboard,
    )
```

**Step 2: Обновить `cmd_start` — добавить ветку мультимастера**

Найти блок в `cmd_start` (строка ~210):

```python
# Check if already registered
client, master, master_client = await get_client_context(tg_id, _active_masters.get(tg_id))
if client and master and master_client:
    await state.clear()
    await show_home(bot, client, master, master_client, message.chat.id, force_new=True)
    return
```

После этого блока (перед `# Extract invite token`) добавить:

```python
# Multi-master: registered but no master selected
if client and not master:
    masters = await get_all_client_masters_by_tg_id(tg_id)
    if masters:
        await show_master_select(bot, tg_id, message.chat.id)
        return
```

**Step 3: Добавить обработчик `select_master` callback**

После обработчика `cb_home` (~строка 597) добавить:

```python
@router.callback_query(F.data.startswith("select_master:"))
async def cb_select_master(callback: CallbackQuery, bot: Bot, state: FSMContext) -> None:
    """Handle master selection from multi-master picker."""
    tg_id = callback.from_user.id
    master_id = int(callback.data.split(":")[1])

    _active_masters[tg_id] = master_id

    client, master, master_client = await get_client_context(tg_id, master_id)
    if not client or not master or not master_client:
        await callback.answer("Ошибка при выборе мастера")
        return

    await callback.message.delete()
    await show_home(bot, client, master, master_client, callback.message.chat.id, force_new=True)
    await callback.answer()
```

**Step 4: Добавить кнопку "Сменить мастера" в `home_client_kb`**

Найти функцию `home_client_kb` в `src/keyboards.py`. Добавить параметр `multi_master: bool = False` и кнопку:

```python
def home_client_kb(multi_master: bool = False) -> InlineKeyboardMarkup:
    # ... существующие кнопки ...
    if multi_master:
        buttons.append([InlineKeyboardButton(text="🔄 Сменить мастера", callback_data="change_master")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
```

**Важно:** `home_client_kb()` вызывается в нескольких местах. Найти вызовы в `client_bot.py`: `grep -n "home_client_kb()" src/client_bot.py`. В `show_home()` и `cb_home()` — передать `multi_master=True` если у клиента несколько мастеров. Для этого `show_home` нужно принять количество мастеров или определять внутри:

Обновить `show_home`:
```python
async def show_home(bot, client, master, master_client, chat_id, force_new=False):
    text = await build_home_text(client, master, master_client)
    all_masters = await get_all_client_masters_by_tg_id(client.tg_id)
    keyboard = home_client_kb(multi_master=len(all_masters) > 1)
    # ... остальная логика без изменений
```

**Step 5: Добавить обработчик `change_master` callback**

```python
@router.callback_query(F.data == "change_master")
async def cb_change_master(callback: CallbackQuery, bot: Bot) -> None:
    """Show master selection screen."""
    tg_id = callback.from_user.id
    await callback.message.delete()
    await show_master_select(bot, tg_id, callback.message.chat.id)
    await callback.answer()
```

**Step 6: Проверить синтаксис**

```bash
python -c "from src.client_bot import router; from src.keyboards import home_client_kb; print('OK')"
```

Ожидаемый вывод: `OK`

**Step 7: Commit**

```bash
git add src/client_bot.py src/keyboards.py
git commit -m "feat(bot): add multi-master selection UI in client_bot"
```

---

### Task 7: Финальная проверка

**Step 1: Проверить все роуты API**

```bash
python -c "
from src.api.app import app
paths = [r.path for r in app.routes]
checks = ['/api/client/masters', '/api/client/link', '/api/me', '/api/orders', '/api/bonuses']
for p in checks:
    assert p in paths, f'MISSING: {p}'
print('All routes OK:', checks)
"
```

**Step 2: Проверить импорты client_bot**

```bash
python -c "
from src.client_bot import router, get_client_context, _active_masters, show_master_select
print('client_bot OK')
"
```

**Step 3: Проверить npm build**

```bash
cd /Users/evgenijpastusenko/Projects/Master_bot/miniapp && npm run build 2>&1 | tail -5
```

Ожидаемый вывод: `✓ built in ...` (фронтенд не затронут, должен собраться без ошибок)

**Step 4: Финальный commit (если были правки)**

```bash
git add -p
git commit -m "fix(multi-master): <описание>"
```

---

## Итог: затронутые файлы

| Файл | Изменение |
|------|-----------|
| `src/database.py` | +3 функции |
| `src/api/dependencies.py` | `get_current_client` + `Query(master_id)` |
| `src/api/routers/client_masters.py` | Новый файл (GET masters, POST link) |
| `src/api/routers/orders.py` | `master_id` в `OrderRequest` |
| `src/api/app.py` | +импорт + include_router |
| `src/client_bot.py` | `get_client_context` + `_active_masters` + UI выбора |
| `src/keyboards.py` | `home_client_kb(multi_master=)` |

## Backward compatibility

- Клиент с 1 мастером и без `?master_id` → работает как раньше
- `client.registered_via` не трогаем (legacy поле)
- Мастерский Mini App и master_bot — не затронуты
