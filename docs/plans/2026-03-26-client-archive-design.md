# Design: Client Archiving

**Date:** 2026-03-26
**Status:** Approved

## Summary

Allow masters to archive clients so they are hidden from the main client list but can be restored later. Follows the existing `is_active` pattern used for services.

## Database

**Migration** `007_client_archive.sql`:
```sql
ALTER TABLE master_clients ADD COLUMN is_archived BOOLEAN DEFAULT FALSE;
```

**Code changes** in `src/database.py`:
- Add `"is_archived"` to `ALLOWED_MASTER_CLIENT_FIELDS`
- `get_clients_paginated` — add `AND mc.is_archived = 0` to WHERE
- `search_clients` — add `AND mc.is_archived = 0` to WHERE
- New: `archive_client(master_id, client_id)` — sets `is_archived = 1`
- New: `restore_client(master_id, client_id)` — sets `is_archived = 0`
- New: `get_archived_clients(master_id)` — returns list of archived clients

## Keyboards (`src/keyboards.py`)

- `client_card_kb(client_id)` — add **📦 В архив** button (`clients:archive:{client_id}`)
- New `client_archive_confirm_kb(client_id)` — two buttons: **✅ Да, в архив** / **❌ Отмена**
- `clients_menu_kb()` (or equivalent) — add **📦 Архив** button (`clients:archive`)
- New `archived_clients_kb(clients)` — list of archived clients, each with **↩️ Восстановить** button

## Handlers (`src/handlers/clients.py`)

| Handler | Trigger | Action |
|---|---|---|
| `cb_client_archive_confirm` | `clients:archive:{client_id}` | Show confirmation screen |
| `cb_client_archive_do` | `clients:archive:do:{client_id}` | Call `archive_client`, return to client list |
| `cb_clients_archive_list` | `clients:archive` | Show list of archived clients |
| `cb_client_restore` | `clients:restore:{client_id}` | Call `restore_client`, refresh archived list |

## UX Flow

```
Client card
  → [📦 В архив]
    → Confirmation screen ("Архивировать клиента X?")
      → [✅ Да] → archive → back to client list
      → [❌ Отмена] → back to client card

Clients menu
  → [📦 Архив]
    → Archived clients list
      → [↩️ Восстановить] per client → restore → refresh list
```

## Out of Scope

- Archived clients are fully hidden from orders, reports, search, notifications
- No bulk archive/restore
- No archive reason/notes
