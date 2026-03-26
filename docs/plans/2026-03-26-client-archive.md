# Client Archive Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Let masters archive clients so they disappear from the main list, with the ability to restore them from a dedicated archive section.

**Architecture:** Add `is_archived` boolean to `master_clients`. Filter it out in existing listing/search queries. Add archive/restore buttons to client card and archive list to the clients menu.

**Tech Stack:** Python 3.11, aiogram 3.x, aiosqlite, SQLite migrations

---

### Task 1: DB migration

**Files:**
- Create: `migrations/007_client_archive.sql`

**Step 1: Create migration file**

```sql
-- migrations/007_client_archive.sql
ALTER TABLE master_clients ADD COLUMN is_archived BOOLEAN DEFAULT FALSE;
```

**Step 2: Apply migration on the server**

The bot applies migrations automatically at startup via `database.py`. Verify the function `init_db` or equivalent calls all migration files — check `src/database.py` top-level `init_db`.

**Step 3: Commit**

```bash
git add migrations/007_client_archive.sql
git commit -m "feat: add is_archived column to master_clients"
```

---

### Task 2: Database functions

**Files:**
- Modify: `src/database.py`

**Step 1: Add `"is_archived"` to `ALLOWED_MASTER_CLIENT_FIELDS`** (line 33)

```python
ALLOWED_MASTER_CLIENT_FIELDS = frozenset({
    "bonus_balance", "total_spent", "note", "first_visit", "last_visit",
    "notify_reminders", "notify_marketing", "notify_24h", "notify_1h", "notify_promos",
    "home_message_id", "is_archived",
})
```

**Step 2: Filter archived in `get_clients_paginated`** (line ~465, 473)

Change both SQL queries (count + data) to add `AND mc.is_archived = 0`:

```python
# Count query:
"SELECT COUNT(*) as cnt FROM master_clients WHERE master_id = ? AND is_archived = 0",

# Data query:
"""
SELECT c.*, mc.bonus_balance
FROM clients c
JOIN master_clients mc ON c.id = mc.client_id
WHERE mc.master_id = ? AND mc.is_archived = 0
ORDER BY c.name
LIMIT ? OFFSET ?
"""
```

**Step 3: Filter archived in `search_clients`** (line ~408, 423)

Add `AND mc.is_archived = 0` to both queries inside `search_clients`:

```python
# Phone search query:
"""
SELECT c.*, mc.bonus_balance
FROM clients c
JOIN master_clients mc ON c.id = mc.client_id
WHERE mc.master_id = ? AND mc.is_archived = 0 AND c.phone LIKE ?
ORDER BY c.name
LIMIT 10
"""

# Name search query:
"""
SELECT c.*, mc.bonus_balance
FROM clients c
JOIN master_clients mc ON c.id = mc.client_id
WHERE mc.master_id = ? AND mc.is_archived = 0
ORDER BY c.name
"""
```

**Step 4: Add `archive_client` and `restore_client` functions**

Add after the existing `update_master_client` function:

```python
async def archive_client(master_id: int, client_id: int) -> None:
    """Archive a client (hide from main list)."""
    await update_master_client(master_id, client_id, is_archived=True)


async def restore_client(master_id: int, client_id: int) -> None:
    """Restore archived client."""
    await update_master_client(master_id, client_id, is_archived=False)
```

**Step 5: Add `get_archived_clients` function**

```python
async def get_archived_clients(master_id: int) -> list[dict]:
    """Get all archived clients for a master."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT c.*, mc.bonus_balance
            FROM clients c
            JOIN master_clients mc ON c.id = mc.client_id
            WHERE mc.master_id = ? AND mc.is_archived = 1
            ORDER BY c.name
            """,
            (master_id,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await conn.close()
```

**Step 6: Commit**

```bash
git add src/database.py
git commit -m "feat: add archive/restore client DB functions"
```

---

### Task 3: Keyboards

**Files:**
- Modify: `src/keyboards.py`

**Step 1: Add 📦 В архив button to `client_card_kb`** (line 233)

```python
def client_card_kb(client_id: int) -> InlineKeyboardMarkup:
    """Client card keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 История", callback_data=f"clients:history:{client_id}"),
            InlineKeyboardButton(text="🎁 Бонусы", callback_data=f"clients:bonus:{client_id}"),
        ],
        [
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"clients:edit:{client_id}"),
            InlineKeyboardButton(text="📝 Заметка", callback_data=f"clients:note:{client_id}"),
        ],
        [InlineKeyboardButton(text="➕ Создать заказ", callback_data=f"clients:order:{client_id}")],
        [InlineKeyboardButton(text="📦 В архив", callback_data=f"clients:archive:confirm:{client_id}")],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="clients"),
            InlineKeyboardButton(text="🏠 Главная", callback_data="home"),
        ],
    ])
```

**Step 2: Add new `client_archive_confirm_kb`**

Add after `client_card_kb`:

```python
def client_archive_confirm_kb(client_id: int) -> InlineKeyboardMarkup:
    """Confirmation keyboard for archiving a client."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, в архив", callback_data=f"clients:archive:do:{client_id}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"clients:view:{client_id}")],
    ])
```

**Step 3: Add 📦 Архив button to `clients_paginated_kb`** (line ~227)

Add before the "Главная" button:

```python
buttons.append([InlineKeyboardButton(text="+ Добавить клиента", callback_data="clients:new")])
buttons.append([InlineKeyboardButton(text="📦 Архив", callback_data="clients:archive")])
buttons.append([InlineKeyboardButton(text="🏠 Главная", callback_data="home")])
```

**Step 4: Add new `archived_clients_kb`**

```python
def archived_clients_kb(clients: list) -> InlineKeyboardMarkup:
    """Archived clients list keyboard."""
    buttons = []
    for client in clients:
        name = client.get("name", "Клиент")
        phone = client.get("phone", "")
        label = name + (f" | {phone}" if phone else "")
        buttons.append([InlineKeyboardButton(
            text=f"↩️ {label}",
            callback_data=f"clients:restore:{client['id']}"
        )])
    if not clients:
        buttons.append([InlineKeyboardButton(text="📭 Архив пуст", callback_data="noop")])
    buttons.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="clients"),
        InlineKeyboardButton(text="🏠 Главная", callback_data="home"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
```

**Step 5: Commit**

```bash
git add src/keyboards.py
git commit -m "feat: add archive/restore keyboard buttons"
```

---

### Task 4: Handlers

**Files:**
- Modify: `src/handlers/clients.py`

**Step 1: Add new imports** (lines 11–38)

Add to `from src.database import (...)`:
```python
    archive_client,
    restore_client,
    get_archived_clients,
```

Add to `from src.keyboards import (...)`:
```python
    client_archive_confirm_kb,
    archived_clients_kb,
```

**Step 2: Add archive confirmation handler**

Add after the `cb_clients_page` handler (around line 100):

```python
@router.callback_query(F.data.startswith("clients:archive:confirm:"))
async def cb_client_archive_confirm(callback: CallbackQuery) -> None:
    """Show archive confirmation screen."""
    client_id = int(callback.data.split(":")[3])
    client = await get_client_with_stats(callback.from_user.id, client_id)
    # get_client_with_stats uses master_id from tg_id — pass master.id instead:
    master = await get_master_by_tg_id(callback.from_user.id)
    client = await get_client_with_stats(master.id, client_id)

    name = client["name"] if client else "Клиент"
    text = (
        f"📦 Архивировать клиента?\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 {name}\n\n"
        "Клиент исчезнет из основного списка.\n"
        "Вы сможете восстановить его из раздела Архив."
    )
    await edit_home_message(callback, text, client_archive_confirm_kb(client_id))
    await callback.answer()
```

**Step 3: Add archive execute handler**

```python
@router.callback_query(F.data.startswith("clients:archive:do:"))
async def cb_client_archive_do(callback: CallbackQuery) -> None:
    """Archive the client."""
    client_id = int(callback.data.split(":")[3])
    master = await get_master_by_tg_id(callback.from_user.id)
    await archive_client(master.id, client_id)

    clients, total = await get_clients_paginated(master.id, page=1)
    total_pages = max(1, (total + 9) // 10)
    text = (
        "👥 Клиенты\n"
        "━━━━━━━━━━━━━━━\n"
        "✅ Клиент перемещён в архив.\n\n"
        "🔍 Введите часть имени/телефона\n"
        "для поиска или выберите из списка.\n"
        f"стр 1 из {total_pages}"
    )
    await edit_home_message(callback, text, clients_paginated_kb(clients, 1, total))
    await callback.answer()
```

**Step 4: Add archive list handler**

```python
@router.callback_query(F.data == "clients:archive")
async def cb_clients_archive_list(callback: CallbackQuery) -> None:
    """Show archived clients list."""
    master = await get_master_by_tg_id(callback.from_user.id)
    clients = await get_archived_clients(master.id)
    text = (
        "📦 Архив клиентов\n"
        "━━━━━━━━━━━━━━━\n"
        f"Архивировано: {len(clients)}\n\n"
        "Нажмите ↩️ чтобы восстановить клиента."
    )
    await edit_home_message(callback, text, archived_clients_kb(clients))
    await callback.answer()
```

**Step 5: Add restore handler**

```python
@router.callback_query(F.data.startswith("clients:restore:"))
async def cb_client_restore(callback: CallbackQuery) -> None:
    """Restore archived client."""
    client_id = int(callback.data.split(":")[2])
    master = await get_master_by_tg_id(callback.from_user.id)
    await restore_client(master.id, client_id)

    clients = await get_archived_clients(master.id)
    text = (
        "📦 Архив клиентов\n"
        "━━━━━━━━━━━━━━━\n"
        f"✅ Клиент восстановлен.\n\n"
        f"Архивировано: {len(clients)}\n\n"
        "Нажмите ↩️ чтобы восстановить клиента."
    )
    await edit_home_message(callback, text, archived_clients_kb(clients))
    await callback.answer()
```

**Step 6: Commit**

```bash
git add src/handlers/clients.py
git commit -m "feat: add archive/restore client handlers"
```

---

### Task 5: Deploy

**Step 1: Push and deploy**

```bash
git push origin main
ssh deploy@75.119.153.118 "cd /opt/master_bot && git pull && docker compose up -d --build master_bot"
```

**Step 2: Apply migration manually** (first deploy only)

```bash
ssh deploy@75.119.153.118 "sqlite3 /opt/master_bot/data/db.sqlite3 'ALTER TABLE master_clients ADD COLUMN is_archived BOOLEAN DEFAULT FALSE;'"
```

**Step 3: Verify**

1. Open master_bot → Клиенты → выбери клиента → должна быть кнопка **📦 В архив**
2. Нажми → экран подтверждения → **✅ Да** → клиент пропал из списка
3. В списке клиентов → **📦 Архив** → клиент там
4. Нажми **↩️** → клиент восстановлен

---

### ⚠️ Note on migration auto-apply

Check whether `init_db()` in `src/database.py` runs all `.sql` files from `migrations/` automatically. If not, the migration must be applied manually (Step 2 in Task 5). Do not add auto-apply logic — it's out of scope.
