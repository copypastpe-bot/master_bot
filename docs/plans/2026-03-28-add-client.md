# Add Client from Mini App — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Мастер может создать клиента из ClientsList (FAB "+") и OrderCreate (поиск не нашёл), с обработкой дубликатов и архивных клиентов.

**Architecture:** Новые эндпоинты в `src/api/routers/master/clients.py` используют существующие DB-функции. Один переиспользуемый `ClientAddSheet.jsx` встроен в оба экрана через `onSuccess(client)` callback. Архивный конфликт обрабатывается прямо внутри sheet без закрытия.

**Tech Stack:** Python/FastAPI + aiosqlite, React 19 + @tanstack/react-query, phonenumbers (уже в deps).

---

### Task 1: POST /api/master/clients

**Files:**
- Modify: `src/api/routers/master/clients.py`
- Modify: `src/api/app.py` — уже импортирован, ничего менять не нужно

**Контекст:**
- `normalize_phone(phone)` из `src/utils.py` → E.164 или None если невалидный
- `get_client_by_phone(phone)` → `Optional[Client]`
- `get_master_client(master_id, client_id)` → `Optional[MasterClient]` с полем `is_archived`
- `create_client(name, tg_id=None, phone=None, birthday=None)` → `Client`
- `link_client_to_master(master_id, client_id)` → `MasterClient`

**Step 1: Добавить импорты в clients.py**

В блок импортов из `src.database` добавить:
```python
get_client_by_phone,
get_master_client,
create_client,
link_client_to_master,
```

В блок импортов из `src.utils`:
```python
from src.utils import normalize_phone
```

**Step 2: Добавить Pydantic модель для тела запроса**

После существующих моделей (найди их по `class.*BaseModel`) добавить:

```python
class ClientCreateRequest(BaseModel):
    name: str
    phone: str
    birthday: Optional[str] = None
```

**Step 3: Добавить эндпоинт**

```python
@router.post("/master/clients", status_code=201)
async def create_master_client(
    body: ClientCreateRequest,
    master: Master = Depends(get_current_master),
):
    """Create or link a client. Handles duplicate phone scenarios."""
    # Validate name
    name = body.name.strip()
    if not name or len(name) > 100:
        raise HTTPException(422, "name must be 1-100 characters")

    # Normalize phone
    normalized_phone = normalize_phone(body.phone)
    if not normalized_phone:
        raise HTTPException(422, "invalid phone number")

    # Validate birthday format if provided
    birthday = body.birthday
    if birthday:
        try:
            from datetime import date as date_cls
            bday = date_cls.fromisoformat(birthday)
            if bday > date_cls.today():
                raise HTTPException(422, "birthday cannot be in the future")
        except ValueError:
            raise HTTPException(422, "birthday must be YYYY-MM-DD")

    # Check if client with this phone exists
    existing = await get_client_by_phone(normalized_phone)

    if existing:
        # Check master-client link
        mc = await get_master_client(master.id, existing.id)
        if mc:
            if not mc.is_archived:
                # Active duplicate
                raise HTTPException(
                    409,
                    detail={"error": "client_exists", "archived": False},
                )
            else:
                # Archived — let frontend decide
                raise HTTPException(
                    409,
                    detail={
                        "error": "client_archived",
                        "archived": True,
                        "client_id": existing.id,
                        "name": existing.name,
                    },
                )
        # Client exists globally but not linked to this master — link them
        await link_client_to_master(master.id, existing.id)
        # Optionally update name/birthday if master provided them
        updates = {}
        if name and name != existing.name:
            updates["name"] = name
        if birthday and birthday != existing.birthday:
            updates["birthday"] = birthday
        if updates:
            await update_client(existing.id, **updates)
        client = existing
        is_new = False
    else:
        # Create brand-new client
        client = await create_client(
            name=name,
            tg_id=None,
            phone=normalized_phone,
            birthday=birthday,
        )
        await link_client_to_master(master.id, client.id)
        is_new = True

    return {
        "id": client.id,
        "name": name if is_new else (client.name or name),
        "phone": normalized_phone,
        "birthday": birthday or client.birthday,
        "bonus_balance": 0,
        "is_new": is_new,
    }
```

**Step 4: Проверка импорта**

```bash
cd /Users/evgenijpastusenko/Projects/Master_bot
python3 -c "from src.api.app import app; print('OK')"
```
Ожидание: `OK`

**Step 5: Commit**

```bash
git add src/api/routers/master/clients.py
git commit -m "feat(api): add POST /master/clients endpoint"
```

---

### Task 2: POST /api/master/clients/{id}/restore

**Files:**
- Modify: `src/api/routers/master/clients.py`

**Контекст:** `restore_client(master_id, client_id)` из `src/database.py` уже существует — вызывает `update_master_client(master_id, client_id, is_archived=False)`.

**Step 1: Добавить импорт `restore_client` в clients.py**

В блок импортов из `src.database` добавить:
```python
restore_client,
```

**Step 2: Добавить эндпоинт**

```python
@router.post("/master/clients/{client_id}/restore")
async def restore_master_client(
    client_id: int,
    master: Master = Depends(get_current_master),
):
    """Restore archived client."""
    mc = await get_master_client(master.id, client_id)
    if not mc:
        raise HTTPException(404, "client not found")
    if not mc.is_archived:
        raise HTTPException(409, "client is not archived")

    await restore_client(master.id, client_id)

    # Return client data for frontend to navigate
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT id, name, phone, birthday FROM clients WHERE id = ?",
            (client_id,)
        )
        row = await cursor.fetchone()
    finally:
        await conn.close()

    if not row:
        raise HTTPException(404, "client not found")

    return {
        "id": row["id"],
        "name": row["name"] or "",
        "phone": row["phone"] or "",
        "birthday": row["birthday"],
        "bonus_balance": mc.bonus_balance or 0,
        "is_new": False,
    }
```

**Step 3: Проверка**

```bash
cd /Users/evgenijpastusenko/Projects/Master_bot
python3 -c "from src.api.app import app; print('OK')"
```

**Step 4: Commit**

```bash
git add src/api/routers/master/clients.py
git commit -m "feat(api): add POST /master/clients/{id}/restore endpoint"
```

---

### Task 3: API функции на фронтенде

**Files:**
- Modify: `miniapp/src/api/client.js`

**Step 1: Добавить в конец файла**

```javascript
// Client creation
export const createMasterClient = (data) =>
  api.post('/api/master/clients', data).then(r => r.data);
// data: { name: string, phone: string, birthday?: string }

export const restoreArchivedClient = (clientId) =>
  api.post(`/api/master/clients/${clientId}/restore`).then(r => r.data);
```

**Step 2: Commit**

```bash
git add miniapp/src/api/client.js
git commit -m "feat(api-client): add createMasterClient and restoreArchivedClient"
```

---

### Task 4: ClientAddSheet компонент

**Files:**
- Create: `miniapp/src/master/components/ClientAddSheet.jsx`

**Контекст:**
- Props: `onSuccess(client)`, `onClose()`
- `onSuccess` вызывается с объектом клиента `{ id, name, phone, ... }`
- Нижний sheet с backdrop — такой же паттерн как `CustomPeriodSheet` в `Reports.jsx`

**Step 1: Создать файл**

```jsx
import { useState } from 'react';
import { createMasterClient, restoreArchivedClient } from '../../api/client';

const WebApp = window.Telegram?.WebApp;

function haptic() {
  if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
    WebApp.HapticFeedback.impactOccurred('light');
  }
}

const inputStyle = {
  width: '100%',
  boxSizing: 'border-box',
  border: '1px solid var(--tg-secondary-bg)',
  borderRadius: 8,
  padding: '10px 12px',
  background: 'var(--tg-surface)',
  color: 'var(--tg-text)',
  fontSize: 15,
  outline: 'none',
};

function FieldLabel({ children }) {
  return (
    <div style={{ fontSize: 12, color: 'var(--tg-hint)', marginBottom: 4 }}>
      {children}
    </div>
  );
}

export default function ClientAddSheet({ onSuccess, onClose }) {
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [birthday, setBirthday] = useState('');
  const [loading, setLoading] = useState(false);
  const [fieldError, setFieldError] = useState(''); // under fields
  // Archived conflict state
  const [archivedClient, setArchivedClient] = useState(null); // { client_id, name }

  const today = new Date().toISOString().slice(0, 10);
  const canSubmit = name.trim().length > 0 && phone.trim().length >= 10;

  const handleSubmit = async () => {
    if (!canSubmit || loading) return;
    haptic();
    setLoading(true);
    setFieldError('');
    try {
      const client = await createMasterClient({
        name: name.trim(),
        phone: phone.trim(),
        birthday: birthday || undefined,
      });
      if (typeof WebApp?.HapticFeedback?.notificationOccurred === 'function') {
        WebApp.HapticFeedback.notificationOccurred('success');
      }
      onSuccess(client);
    } catch (err) {
      const data = err?.response?.data;
      if (err?.response?.status === 409) {
        if (data?.archived === true) {
          // Show unarchive confirmation view
          setArchivedClient({ client_id: data.client_id, name: data.name });
        } else {
          setFieldError('Клиент с таким номером уже есть');
        }
      } else if (err?.response?.status === 422) {
        const msg = typeof data === 'string' ? data : (data?.detail || 'Проверьте данные');
        setFieldError(typeof msg === 'string' ? msg : 'Проверьте данные');
      } else {
        setFieldError('Не удалось добавить клиента');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleRestore = async () => {
    if (!archivedClient || loading) return;
    haptic();
    setLoading(true);
    try {
      const client = await restoreArchivedClient(archivedClient.client_id);
      if (typeof WebApp?.HapticFeedback?.notificationOccurred === 'function') {
        WebApp.HapticFeedback.notificationOccurred('success');
      }
      onSuccess(client);
    } catch {
      setFieldError('Не удалось разархивировать');
      setArchivedClient(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 100 }}
      />

      {/* Sheet */}
      <div style={{
        position: 'fixed', bottom: 0, left: 0, right: 0, zIndex: 101,
        background: 'var(--tg-bg)',
        borderRadius: '16px 16px 0 0',
        padding: '20px 16px 32px',
      }}>
        {archivedClient ? (
          /* ── Archived conflict view ── */
          <>
            <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--tg-text)', marginBottom: 12 }}>
              Клиент уже есть
            </div>
            <div style={{ fontSize: 14, color: 'var(--tg-hint)', marginBottom: 20 }}>
              Клиент <strong style={{ color: 'var(--tg-text)' }}>{archivedClient.name}</strong> с
              таким номером находится в архиве. Разархивировать?
            </div>
            {fieldError && (
              <div style={{ color: '#e53935', fontSize: 13, marginBottom: 12 }}>{fieldError}</div>
            )}
            <div style={{ display: 'flex', gap: 10 }}>
              <button
                onClick={onClose}
                style={{
                  flex: 1, padding: '13px', borderRadius: 12, border: '1px solid var(--tg-secondary-bg)',
                  background: 'none', color: 'var(--tg-text)', fontSize: 15, cursor: 'pointer',
                }}
              >
                Отмена
              </button>
              <button
                onClick={handleRestore}
                disabled={loading}
                style={{
                  flex: 2, padding: '13px', borderRadius: 12, border: 'none',
                  background: loading ? 'var(--tg-hint)' : 'var(--tg-button)',
                  color: 'var(--tg-button-text)', fontSize: 15, fontWeight: 600, cursor: 'pointer',
                }}
              >
                {loading ? 'Загрузка...' : 'Разархивировать'}
              </button>
            </div>
          </>
        ) : (
          /* ── Add client form ── */
          <>
            <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--tg-text)', marginBottom: 16 }}>
              Новый клиент
            </div>

            <div style={{ marginBottom: 12 }}>
              <FieldLabel>Имя *</FieldLabel>
              <input
                type="text"
                value={name}
                onChange={e => { setName(e.target.value); setFieldError(''); }}
                placeholder="Иван Петров"
                style={inputStyle}
              />
            </div>

            <div style={{ marginBottom: 12 }}>
              <FieldLabel>Телефон *</FieldLabel>
              <input
                type="tel"
                value={phone}
                onChange={e => { setPhone(e.target.value); setFieldError(''); }}
                placeholder="+7 999 123 45 67"
                style={inputStyle}
              />
            </div>

            <div style={{ marginBottom: 16 }}>
              <FieldLabel>Дата рождения (необязательно)</FieldLabel>
              <input
                type="date"
                value={birthday}
                max={today}
                onChange={e => setBirthday(e.target.value)}
                style={inputStyle}
              />
              <div style={{ fontSize: 11, color: 'var(--tg-hint)', marginTop: 3 }}>
                Для бонуса на день рождения
              </div>
            </div>

            {fieldError && (
              <div style={{ color: '#e53935', fontSize: 13, marginBottom: 10 }}>{fieldError}</div>
            )}

            <button
              onClick={handleSubmit}
              disabled={!canSubmit || loading}
              style={{
                width: '100%', padding: '14px', borderRadius: 12, border: 'none',
                background: canSubmit && !loading ? 'var(--tg-button)' : 'var(--tg-hint)',
                color: 'var(--tg-button-text)', fontSize: 15, fontWeight: 600,
                cursor: canSubmit && !loading ? 'pointer' : 'default',
              }}
            >
              {loading ? 'Загрузка...' : 'Добавить клиента'}
            </button>
          </>
        )}
      </div>
    </>
  );
}
```

**Step 2: Commit**

```bash
git add miniapp/src/master/components/ClientAddSheet.jsx
git commit -m "feat(ClientAddSheet): add reusable client creation bottom sheet"
```

---

### Task 5: Встраивание в ClientsList

**Files:**
- Modify: `miniapp/src/master/pages/ClientsList.jsx`

**Контекст:**
- `ClientsList` принимает `onNavigate` prop
- Список управляется через `useState` + ручной fetch (не React Query)
- Для обновления списка после добавления: сбросить `query`, `page` и `clients` + принудительно перезагрузить через `setDebouncedQuery('')` и `setPage(1)`
- FAB — абсолютно позиционированная кнопка "+" в правом нижнем углу, как в Calendar

**Step 1: Добавить импорт ClientAddSheet**

```jsx
import ClientAddSheet from '../components/ClientAddSheet';
```

**Step 2: Добавить state для sheet**

В список useState добавить:
```jsx
const [showAddSheet, setShowAddSheet] = useState(false);
```

**Step 3: Добавить handler после успешного создания**

```jsx
const handleClientAdded = (client) => {
  haptic('medium');
  setShowAddSheet(false);
  // Refresh list
  setQuery('');
  setDebouncedQuery('');
  setClients([]);
  setPage(1);
  setTotalPages(1);
  // Navigate to the new client card
  onNavigate('client', { id: client.id });
};
```

**Step 4: Добавить FAB кнопку перед закрывающим `</div>` компонента**

```jsx
{/* FAB: Add client */}
<button
  onClick={() => { haptic(); setShowAddSheet(true); }}
  style={{
    position: 'fixed',
    bottom: 90,
    right: 20,
    width: 52,
    height: 52,
    borderRadius: '50%',
    background: 'var(--tg-button)',
    color: 'var(--tg-button-text)',
    border: 'none',
    fontSize: 26,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'pointer',
    boxShadow: '0 2px 12px rgba(0,0,0,0.25)',
    zIndex: 20,
  }}
>
  +
</button>

{showAddSheet && (
  <ClientAddSheet
    onSuccess={handleClientAdded}
    onClose={() => setShowAddSheet(false)}
  />
)}
```

**Step 5: Commit**

```bash
git add miniapp/src/master/pages/ClientsList.jsx
git commit -m "feat(ClientsList): add FAB and ClientAddSheet integration"
```

---

### Task 6: Встраивание в OrderCreate (StepClient)

**Files:**
- Modify: `miniapp/src/master/pages/OrderCreate.jsx`

**Контекст:**
- `StepClient` принимает props: `selected`, `onSelect`, `onNext`
- Кнопка "+ Добавить нового клиента" показывается только когда `!isFetching && clients.length === 0 && debouncedQuery.length > 0` (строки ~174-178)
- После успешного добавления: `onSelect(client)` + `onNext()` (переход на шаг 2)

**Step 1: Добавить импорт ClientAddSheet в OrderCreate.jsx**

```jsx
import ClientAddSheet from '../components/ClientAddSheet';
```

**Step 2: Добавить state в StepClient**

```jsx
const [showAddSheet, setShowAddSheet] = useState(false);
```

**Step 3: Добавить кнопку после блока "Клиенты не найдены"**

Найти строку:
```jsx
{!isFetching && clients.length === 0 && (
  <div style={{ textAlign: 'center', color: 'var(--tg-hint)', fontSize: 13, padding: 12 }}>
    Клиенты не найдены
  </div>
)}
```

Заменить на:
```jsx
{!isFetching && clients.length === 0 && (
  <div style={{ textAlign: 'center' }}>
    <div style={{ color: 'var(--tg-hint)', fontSize: 13, padding: '12px 0 8px' }}>
      Клиенты не найдены
    </div>
    <button
      onClick={() => { haptic(); setShowAddSheet(true); }}
      style={{
        width: '100%',
        padding: '11px 16px',
        background: 'none',
        border: '1.5px solid var(--tg-button)',
        borderRadius: 10,
        color: 'var(--tg-button)',
        fontSize: 14,
        fontWeight: 600,
        cursor: 'pointer',
      }}
    >
      + Добавить нового клиента
    </button>
  </div>
)}
```

**Step 4: Добавить ClientAddSheet в конец return StepClient**

Перед закрывающим `</div>` в StepClient добавить:
```jsx
{showAddSheet && (
  <ClientAddSheet
    onSuccess={(client) => {
      haptic();
      setShowAddSheet(false);
      onSelect(client);
      onNext();
    }}
    onClose={() => setShowAddSheet(false)}
  />
)}
```

**Step 5: Commit**

```bash
git add miniapp/src/master/pages/OrderCreate.jsx
git commit -m "feat(OrderCreate): add client creation from search empty state"
```

---

### Task 7: Финальная проверка сборки

**Step 1: Запустить сборку**

```bash
cd /Users/evgenijpastusenko/Projects/Master_bot/miniapp
npm run build
```
Ожидание: `✓ built in X.Xs` без ошибок.

**Step 2: Проверить backend**

```bash
cd /Users/evgenijpastusenko/Projects/Master_bot
python3 -c "from src.api.app import app; print([r.path for r in app.routes if 'clients' in str(r.path)])"
```
Ожидание: список с `/api/master/clients` и `/api/master/clients/{client_id}/restore`.

**Step 3: Commit если были автоматические изменения**

```bash
git status --short
# если пусто — всё уже закоммичено
```
