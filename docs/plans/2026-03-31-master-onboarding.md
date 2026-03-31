# Master Mini App Onboarding Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Добавить регистрацию мастера через Mini App — мульти-степ онбординг вместо экрана "Зарегистрируйтесь через бота".

**Architecture:** Новый эндпоинт `POST /api/master/register` в отдельном роутере `src/api/routers/master/auth.py`. Фронтенд — компонент `MasterOnboarding.jsx` с 3 шагами, заменяет `UnknownRoleScreen` в `App.jsx`. Бот-регистрация продолжает работать параллельно.

**Tech Stack:** FastAPI (Python), React (JSX), axios, Telegram WebApp JS SDK

---

### Task 1: Добавить MASTER_BOT_USERNAME в конфиг

**Files:**
- Modify: `src/config.py:11`

**Step 1: Добавить переменную**

В файле `src/config.py` после строки `CLIENT_BOT_USERNAME`:

```python
CLIENT_BOT_USERNAME: str = os.getenv("CLIENT_BOT_USERNAME", "")
MASTER_BOT_USERNAME: str = os.getenv("MASTER_BOT_USERNAME", "")
```

**Step 2: Проверить что .env содержит переменную**

```bash
grep MASTER_BOT_USERNAME .env 2>/dev/null || echo "нужно добавить MASTER_BOT_USERNAME в .env"
```

Если не найдено — добавить в `.env`:
```
MASTER_BOT_USERNAME=your_master_bot_username_here
```

**Step 3: Commit**

```bash
git add src/config.py
git commit -m "feat(config): add MASTER_BOT_USERNAME env variable"
```

---

### Task 2: Создать эндпоинт POST /api/master/register

**Files:**
- Create: `src/api/routers/master/auth.py`

**Step 1: Создать файл роутера**

```python
"""Master registration endpoint."""

from typing import Optional
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from src.api.auth import validate_init_data, extract_tg_id
from src.config import MASTER_BOT_TOKEN, MASTER_BOT_USERNAME
from src.database import get_master_by_tg_id, create_master
from src.utils import generate_invite_token

router = APIRouter(tags=["master-auth"])


class RegisterMasterRequest(BaseModel):
    name: str
    sphere: Optional[str] = None
    contacts: Optional[str] = None
    work_hours: Optional[str] = None


@router.post("/master/register")
async def register_master(
    body: RegisterMasterRequest,
    x_init_data: Optional[str] = Header(None, alias="X-Init-Data"),
):
    """
    Register a new master via Mini App.
    Returns 409 if master with this tg_id already exists.
    No dev-bypass — requires real Telegram initData.
    """
    if not x_init_data:
        raise HTTPException(status_code=401, detail="Missing X-Init-Data header")

    validated = validate_init_data(x_init_data, MASTER_BOT_TOKEN)
    if not validated:
        raise HTTPException(status_code=401, detail="Invalid initData")

    tg_id = extract_tg_id(validated)
    if not tg_id:
        raise HTTPException(status_code=401, detail="No user data in initData")

    existing = await get_master_by_tg_id(tg_id)
    if existing:
        raise HTTPException(status_code=409, detail="Master already registered")

    if not body.name or not body.name.strip():
        raise HTTPException(status_code=422, detail="Name is required")

    invite_token = generate_invite_token()
    master = await create_master(
        tg_id=tg_id,
        name=body.name.strip(),
        invite_token=invite_token,
        sphere=body.sphere or None,
        contacts=body.contacts or None,
        work_hours=body.work_hours or None,
    )

    invite_link = f"https://t.me/{MASTER_BOT_USERNAME}?start={invite_token}"

    return {
        "id": master.id,
        "name": master.name,
        "invite_token": invite_token,
        "invite_link": invite_link,
        "role": "master",
    }
```

**Step 2: Commit**

```bash
git add src/api/routers/master/auth.py
git commit -m "feat(api): add POST /api/master/register endpoint"
```

---

### Task 3: Подключить роутер в app.py

**Files:**
- Modify: `src/api/app.py`

**Step 1: Добавить импорт и include_router**

В `src/api/app.py` добавить после последнего импорта роутера мастера:

```python
from src.api.routers.master import auth as master_auth
```

И после последнего `app.include_router(...)`:

```python
app.include_router(master_auth.router, prefix="/api")
```

**Step 2: Проверить что сервер запускается**

```bash
cd /Users/evgenijpastusenko/Projects/Master_bot
python -c "from src.api.app import app; print('OK')"
```

Ожидаемый вывод: `OK`

**Step 3: Commit**

```bash
git add src/api/app.py
git commit -m "feat(api): register master auth router in app"
```

---

### Task 4: Добавить registerMaster в API клиент фронтенда

**Files:**
- Modify: `miniapp/src/api/client.js`

**Step 1: Добавить функцию**

В конец файла `miniapp/src/api/client.js`:

```javascript
// Master registration (onboarding)
export const registerMaster = (data) =>
  api.post('/master/register', data).then(r => r.data);
```

`data` — объект `{ name, sphere?, contacts?, work_hours? }`

**Step 2: Commit**

```bash
git add miniapp/src/api/client.js
git commit -m "feat(miniapp): add registerMaster API function"
```

---

### Task 5: Создать компонент MasterOnboarding

**Files:**
- Create: `miniapp/src/master/pages/MasterOnboarding.jsx`

**Step 1: Создать компонент**

```jsx
import { useState } from 'react';
import { registerMaster } from '../../api/client';

const WebApp = window.Telegram?.WebApp;

const DOT_STYLE = (active) => ({
  width: 8,
  height: 8,
  borderRadius: '50%',
  background: active ? 'var(--tg-button)' : 'var(--tg-hint)',
  opacity: active ? 1 : 0.35,
  transition: 'all 0.2s',
});

const INPUT_STYLE = {
  width: '100%',
  padding: '12px 14px',
  borderRadius: 12,
  border: '1.5px solid var(--tg-hint)',
  background: 'var(--tg-bg)',
  color: 'var(--tg-text)',
  fontSize: 16,
  outline: 'none',
  boxSizing: 'border-box',
};

const BTN_PRIMARY = {
  width: '100%',
  padding: '14px',
  borderRadius: 12,
  border: 'none',
  background: 'var(--tg-button)',
  color: 'var(--tg-button-text)',
  fontSize: 16,
  fontWeight: 600,
  cursor: 'pointer',
};

const BTN_SECONDARY = {
  width: '100%',
  padding: '12px',
  borderRadius: 12,
  border: '1.5px solid var(--tg-hint)',
  background: 'transparent',
  color: 'var(--tg-hint)',
  fontSize: 15,
  cursor: 'pointer',
  marginTop: 10,
};

export default function MasterOnboarding({ onRegistered }) {
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({ name: '', sphere: '', contacts: '', work_hours: '' });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const update = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }));

  const submit = async (skipOptional = false) => {
    setLoading(true);
    setError('');
    try {
      const payload = { name: form.name.trim() };
      if (!skipOptional) {
        if (form.sphere.trim()) payload.sphere = form.sphere.trim();
        if (form.contacts.trim()) payload.contacts = form.contacts.trim();
        if (form.work_hours.trim()) payload.work_hours = form.work_hours.trim();
      }
      const data = await registerMaster(payload);
      setResult(data);
      WebApp?.HapticFeedback?.notificationOccurred('success');
      setStep(3);
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Ошибка. Попробуйте ещё раз.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const copyLink = () => {
    const link = result?.invite_link || '';
    if (WebApp?.copyToClipboard) {
      WebApp.copyToClipboard(link);
    } else {
      navigator.clipboard?.writeText(link);
    }
    WebApp?.HapticFeedback?.selectionChanged();
  };

  const handleStart = () => {
    if (WebApp?.MainButton) {
      WebApp.MainButton.hide();
    }
    onRegistered();
  };

  // Show Telegram MainButton on step 3
  if (step === 3 && WebApp?.MainButton) {
    WebApp.MainButton.setText('Начать работу');
    WebApp.MainButton.show();
    WebApp.MainButton.onClick(handleStart);
  }

  return (
    <div style={{ padding: '32px 20px', maxWidth: 420, margin: '0 auto' }}>
      {/* Progress dots */}
      <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginBottom: 36 }}>
        {[1, 2, 3].map((n) => <div key={n} style={DOT_STYLE(step === n)} />)}
      </div>

      {step === 1 && (
        <>
          <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--tg-text)', marginBottom: 8 }}>
            Добро пожаловать в CRMfit!
          </div>
          <div style={{ fontSize: 15, color: 'var(--tg-hint)', marginBottom: 32 }}>
            Настроим ваш профиль за 1 минуту
          </div>
          <div style={{ marginBottom: 24 }}>
            <label style={{ fontSize: 13, color: 'var(--tg-hint)', display: 'block', marginBottom: 6 }}>
              Ваше имя или псевдоним
            </label>
            <input
              style={INPUT_STYLE}
              placeholder="Например: Анна"
              value={form.name}
              onChange={update('name')}
              autoFocus
            />
          </div>
          {error && <div style={{ color: '#e53935', fontSize: 13, marginBottom: 12 }}>{error}</div>}
          <button
            style={{ ...BTN_PRIMARY, opacity: form.name.trim() ? 1 : 0.5 }}
            disabled={!form.name.trim() || loading}
            onClick={() => setStep(2)}
          >
            Далее
          </button>
        </>
      )}

      {step === 2 && (
        <>
          <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--tg-text)', marginBottom: 8 }}>
            Расскажите о себе
          </div>
          <div style={{ fontSize: 14, color: 'var(--tg-hint)', marginBottom: 28 }}>
            Всё необязательно — можно заполнить позже
          </div>

          {[
            { field: 'sphere', label: 'Сфера деятельности', placeholder: 'Например: клининг, парикмахер, репетитор' },
            { field: 'contacts', label: 'Контакты для клиентов', placeholder: 'Телефон, мессенджеры' },
            { field: 'work_hours', label: 'Режим работы', placeholder: 'Например: Пн-Пт 9:00-18:00' },
          ].map(({ field, label, placeholder }) => (
            <div key={field} style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 13, color: 'var(--tg-hint)', display: 'block', marginBottom: 6 }}>
                {label}
              </label>
              <input
                style={INPUT_STYLE}
                placeholder={placeholder}
                value={form[field]}
                onChange={update(field)}
              />
            </div>
          ))}

          {error && <div style={{ color: '#e53935', fontSize: 13, marginBottom: 12 }}>{error}</div>}

          <button style={BTN_PRIMARY} disabled={loading} onClick={() => submit(false)}>
            {loading ? 'Сохраняем...' : 'Далее'}
          </button>
          <button style={BTN_SECONDARY} disabled={loading} onClick={() => submit(true)}>
            Пропустить
          </button>
        </>
      )}

      {step === 3 && result && (
        <>
          <div style={{ textAlign: 'center', marginBottom: 32 }}>
            <div style={{
              fontSize: 64,
              animation: 'popIn 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275)',
            }}>
              ✅
            </div>
            <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--tg-text)', marginTop: 16 }}>
              Профиль создан!
            </div>
            <div style={{ fontSize: 14, color: 'var(--tg-hint)', marginTop: 8 }}>
              Поделитесь ссылкой с клиентами
            </div>
          </div>

          <div style={{
            background: 'var(--tg-secondary-bg)',
            borderRadius: 12,
            padding: '12px 14px',
            marginBottom: 12,
            display: 'flex',
            alignItems: 'center',
            gap: 10,
          }}>
            <div style={{
              flex: 1,
              fontSize: 13,
              color: 'var(--tg-hint)',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}>
              {result.invite_link}
            </div>
            <button
              onClick={copyLink}
              style={{
                border: 'none',
                background: 'var(--tg-button)',
                color: 'var(--tg-button-text)',
                borderRadius: 8,
                padding: '6px 12px',
                fontSize: 13,
                cursor: 'pointer',
                flexShrink: 0,
              }}
            >
              Копировать
            </button>
          </div>

          {/* MainButton "Начать работу" is set above — fallback button if MainButton not available */}
          {!WebApp?.MainButton && (
            <button style={{ ...BTN_PRIMARY, marginTop: 16 }} onClick={handleStart}>
              Начать работу
            </button>
          )}
        </>
      )}

      <style>{`
        @keyframes popIn {
          0% { transform: scale(0); opacity: 0; }
          100% { transform: scale(1); opacity: 1; }
        }
      `}</style>
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add miniapp/src/master/pages/MasterOnboarding.jsx
git commit -m "feat(miniapp): add MasterOnboarding multi-step form"
```

---

### Task 6: Обновить App.jsx

**Files:**
- Modify: `miniapp/src/App.jsx`

**Step 1: Добавить импорт MasterOnboarding**

В начало файла после существующих импортов:

```jsx
import MasterOnboarding from './master/pages/MasterOnboarding';
```

**Step 2: Заменить UnknownRoleScreen**

Найти в `App()` блок:
```jsx
return <UnknownRoleScreen />;
```

Заменить на:
```jsx
return <MasterOnboarding onRegistered={() => setRole('master')} />;
```

**Step 3: Удалить компонент UnknownRoleScreen**

Удалить из файла всю функцию `UnknownRoleScreen` (строки 42–54 в текущей версии):

```jsx
// Удалить целиком:
function UnknownRoleScreen() {
  return (
    <div style={{ textAlign: 'center', padding: '64px 24px' }}>
      ...
    </div>
  );
}
```

**Step 4: Проверить сборку**

```bash
cd miniapp && npm run build 2>&1 | tail -20
```

Ожидаемый вывод: `✓ built in ...` без ошибок.

**Step 5: Commit**

```bash
git add miniapp/src/App.jsx
git commit -m "feat(miniapp): show MasterOnboarding for unknown role instead of error screen"
```

---

### Task 7: Финальная проверка

**Проверка 1 — Бэкенд запускается**

```bash
cd /Users/evgenijpastusenko/Projects/Master_bot
python -c "from src.api.app import app; routes = [r.path for r in app.routes]; assert '/api/master/register' in routes, routes; print('OK — /api/master/register найден')"
```

**Проверка 2 — Дублированная регистрация даёт 409**

Логика: вызов `POST /api/master/register` с уже существующим `tg_id` → 409.
Проверяется вручную или через интеграционный тест (нет pytest в проекте).

**Проверка 3 — Фронтенд собирается**

```bash
cd /Users/evgenijpastusenko/Projects/Master_bot/miniapp && npm run build
```

Ожидаемый вывод: `✓ built in ...` без предупреждений об ошибках.

**Step: Commit (если нужны правки по результатам проверки)**

```bash
git add -p
git commit -m "fix(onboarding): <описание правки>"
```

---

## Итог: затронутые файлы

| Файл | Действие |
|------|----------|
| `src/config.py` | +1 строка: `MASTER_BOT_USERNAME` |
| `src/api/routers/master/auth.py` | Создать (новый) |
| `src/api/app.py` | +2 строки: импорт + include_router |
| `miniapp/src/api/client.js` | +2 строки: `registerMaster` |
| `miniapp/src/master/pages/MasterOnboarding.jsx` | Создать (новый) |
| `miniapp/src/App.jsx` | Удалить `UnknownRoleScreen`, добавить импорт и `MasterOnboarding` |
