# Add Client from Mini App — Design

## Goal
Мастер может добавить клиента прямо из Mini App: из списка клиентов (FAB "+") или при создании заказа (поиск не нашёл клиента).

## Architecture

**Backend:** новый `POST /api/master/clients` в `src/api/routers/master/clients.py` + `POST /api/master/clients/{id}/restore`. Использует существующие `get_client_by_phone`, `create_client`, `link_client_to_master`, `restore_client`, `normalize_phone`.

**Frontend:** один переиспользуемый `ClientAddSheet.jsx` (bottom sheet) встроен в `ClientsList` и `OrderCreate` через `onSuccess(client)` callback.

## Scenarios

| Телефон | Действие | HTTP |
|---|---|---|
| Не найден | create + link | 201, is_new:true |
| Найден, не привязан | link | 200, is_new:false |
| Привязан, активен | — | 409, archived:false |
| Привязан, архив | — | 409, archived:true, client_id:N |

## After success
- **ClientsList:** invalidate query + navigate to client card
- **OrderCreate:** onSelect(client) + onNext() → шаг 2

## Archived client flow
409 с `archived:true` → sheet меняет вид на подтверждение "Разархивировать?". Да → `POST /master/clients/{id}/restore` → onSuccess. Нет → закрыть sheet.

## New endpoints
- `POST /api/master/clients` — создать/привязать клиента
- `POST /api/master/clients/{id}/restore` — разархивировать
