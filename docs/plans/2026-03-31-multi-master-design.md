# Design: Бэкенд-поддержка мультимастерности

**Дата:** 2026-03-31

## Контекст

Клиент привязан к одному мастеру через `clients.registered_via`. Таблица `master_clients` уже поддерживает N:N (`UNIQUE(master_id, client_id)`), но код жёстко работает с одним мастером: `get_master_client_by_client_tg_id` имеет `LIMIT 1`, `get_client_context` читает `client.registered_via`. Нужно снять это ограничение.

**Фронтенд клиентского Mini App — вне скоупа**, только backend + client_bot.

## Архитектура

### 1. database.py — три новые функции

**`get_client_masters(client_id: int) -> list[dict]`**

```sql
SELECT m.id as master_id, m.name as master_name, m.sphere,
       mc.bonus_balance, mc.last_visit,
       (SELECT COUNT(*) FROM orders
        WHERE master_id = m.id AND client_id = ? AND status = 'done') as order_count
FROM masters m
JOIN master_clients mc ON m.id = mc.master_id
WHERE mc.client_id = ?
ORDER BY mc.last_visit DESC NULLS LAST
```

**`get_all_client_masters_by_tg_id(tg_id: int) -> list[dict]`**

Обёртка: `get_client_by_tg_id(tg_id)` → `get_client_masters(client.id)`. Возвращает `[]` если клиент не найден.

**`link_existing_client_to_master(client_id: int, master_id: int) -> bool`**

`INSERT INTO master_clients (master_id, client_id) VALUES (?, ?) ON CONFLICT DO NOTHING`. Возвращает `True` если запись создана, `False` если уже существовала. Welcome bonus начисляется отдельно через `accrue_welcome_bonus()`.

---

### 2. dependencies.py — обновить get_current_client

Добавить `master_id: Optional[int] = Query(None)`. Все 5 роутеров не трогаем — они автоматически получают новое поведение.

Логика:
1. Валидация initData — без изменений
2. `get_client_by_tg_id(tg_id)` → 404 если не найден
3. `get_all_client_masters_by_tg_id(tg_id)` → список
4. Если мастеров == 0 → 404 `"Не привязан ни к одному мастеру"`
5. Если `master_id` указан → найти в списке → 403 если не в списке
6. Если не указан и мастеров == 1 → взять единственного (backward compat)
7. Если не указан и мастеров > 1 → 400 `"Укажите master_id"`

Dev-bypass: без изменений (возвращает первого мастера из БД).

---

### 3. Новые API эндпоинты

**Новый файл:** `src/api/routers/client_masters.py`

```
GET /api/client/masters
Header: X-Init-Data
→ { "masters": [...], "count": N }
```

Использует только `x_init_data` (не `get_current_client`), т.к. не нужен конкретный мастер.

```
POST /api/client/link
Header: X-Init-Data
Body: {"invite_token": "abc123"}
→ 200: { master_id, name, sphere, bonus_balance }
→ 404: мастер не найден
→ 409: уже привязан
```

Логика: найти мастера по token → `link_existing_client_to_master` → при `True` вызвать `accrue_welcome_bonus`.

Подключить в `app.py`.

**Обновить `OrderRequest` в `orders.py`:**

```python
class OrderRequest(BaseModel):
    service_name: str
    master_id: Optional[int] = None
    comment: Optional[str] = None
```

Backward compat: если `master_id` не в body — мастер берётся из dependency как раньше.

---

### 4. client_bot.py — get_client_context + мультимастерный UI

**Обновить сигнатуру:**

```python
async def get_client_context(tg_id: int, master_id: int = None) -> tuple:
```

Логика:
- `masters = await get_all_client_masters_by_tg_id(tg_id)`
- Если `master_id` передан → найти конкретного, вернуть `(client, master, mc)`
- Если мастеров == 1 → backward compat, вернуть единственного
- Если мастеров > 1 и `master_id` не передан → `return client, None, None`

**Обновить `cmd_start` и Home:**

- Если `get_client_context` вернул `(client, None, None)` И `masters` не пуст → показать инлайн-кнопки со списком мастеров
- После выбора: сохранить `active_master_id` в FSM state → вызвать `get_client_context(tg_id, active_master_id)` → показать Home
- Добавить кнопку "🔄 Сменить мастера" в Home (видна только если мастеров > 1)

**Все остальные места с `get_client_context(tg_id)`** (~11 штук) — читать `active_master_id` из FSM state и передавать: `await get_client_context(tg_id, await state.get_data().get('active_master_id'))`.

---

## Затронутые файлы

| Файл | Действие |
|------|----------|
| `src/database.py` | +3 функции |
| `src/api/dependencies.py` | Обновить `get_current_client` |
| `src/api/routers/client_masters.py` | Создать (GET masters, POST link) |
| `src/api/routers/orders.py` | `master_id` в `OrderRequest` |
| `src/api/app.py` | Подключить `client_masters` роутер |
| `src/client_bot.py` | `get_client_context` + мультимастерный UI |

## Что НЕ входит

- Клиентский Mini App (выбор мастера на фронте)
- Клиентская регистрация через Mini App
- Удаление привязки к мастеру
- Изменение `clients.registered_via` (оставить как legacy)

## Критерии приёмки

1. `GET /api/client/masters` → список мастеров
2. Клиентские эндпоинты с `?master_id=1` → работают
3. Без `master_id` при 1 мастере → как раньше
4. Без `master_id` при 2+ мастерах → 400
5. `POST /api/client/link` → привязка к новому мастеру
6. Дублирование → 409
7. client_bot при 1 мастере → как раньше
8. client_bot при 2+ мастерах → показывает выбор
9. Мастерский Mini App и master_bot не сломались
10. `npm run build` без ошибок
